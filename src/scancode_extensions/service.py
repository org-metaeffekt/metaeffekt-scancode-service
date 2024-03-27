import asyncio
import dataclasses
import logging
import operator
import os
import time
import uuid
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import field
from functools import reduce, partial
from pathlib import Path
from threading import Thread
from typing import Any

import click
import uvicorn
from cluecode.plugin_copyright import CopyrightScanner
from fastapi import FastAPI
from formattedcode.output_json import JsonPrettyOutput
from licensedcode.plugin_license import LicenseScanner
from pydantic import BaseModel
from scancode.api import get_licenses, get_file_info
from scancode.plugin_info import InfoScanner

from scancode_extensions.allrights_plugin import allrights_scanner
from scancode_extensions.resource import ScancodeCodebase as Codebase
from scancode_extensions.utils import compute_scanroot_relative, timings

log = logging.getLogger("scanservice")

scancode_config = dict(output_dir="/tmp")


@dataclasses.dataclass
class Scan:
    base: str
    output_file: str
    results: list = field(default_factory=list)
    uuid: uuid = field(default_factory=uuid.uuid4)

    async def create_events(self):
        for _root, dirs, files in os.walk(self.base, topdown=False):
            for name in files:
                full_path = os.path.join(_root, name)
                yield ScanEvent(uuid=self.uuid, location=full_path,
                                relative_path=compute_scanroot_relative(full_path, self.base))


@dataclasses.dataclass
class ScanEvent:
    uuid: str
    location: str
    relative_path: str


class AsynchronousScan:

    def __init__(self):
        self.tasks = set()
        number_processes = 12
        self.executor = ProcessPoolExecutor(number_processes)
        self.thread_executor = ThreadPoolExecutor(2)

        self.scanners = [get_file_info, get_licenses, allrights_scanner]
        self.plugins = [InfoScanner, CopyrightScanner, LicenseScanner, ]

    def shutdown(self):
        log.error("Shutdown executor.")
        self.executor.shutdown(cancel_futures=True)

    @property
    def resource_attributes(self):
        attributes = {}
        for plugin in self.plugins:
            attributes.update(plugin.resource_attributes)
        return attributes

    @property
    def codebase_attributes(self):
        attributes = {}
        for plugin in self.plugins:
            attributes.update(plugin.codebase_attributes)
        return attributes

    async def execute(self, scan_request: "ScanRequest"):
        single_scan = Scan(scan_request.scan_path, scan_request.output_file)
        log.info(f"Scan with uuid {single_scan.uuid}: Scanning dir {single_scan.base}.")
        await self.schedule_scan(single_scan)
        return single_scan.uuid

    async def schedule_scan(self, single_scan):
        future = asyncio.create_task(self.scan_base(single_scan), name=str(single_scan.uuid))
        future.add_done_callback(self.tasks.discard)
        future.uuid = str(single_scan.uuid)
        self.tasks.add(future)

    def write_to_json(self, json_file: Path, codebase: Codebase) -> None:
        plugin = JsonPrettyOutput()
        runner = timings(partial(plugin.process_codebase, output_json_pp=str(json_file), info=True, codebase=codebase))
        self.thread_executor.submit(runner)

    async def scan_base(self, single_scan: Scan):
        start = time.perf_counter()
        codebase = await self.create_codebase(single_scan.base)
        await self.scan_files(single_scan, codebase)
        self.write_to_json(single_scan.output_file, codebase)
        log.warning(f"Scan with uuid {single_scan.uuid} has total scan time: {time.perf_counter() - start}")
        return single_scan

    @timings
    async def create_codebase(self, base):
        return Codebase(location=base, codebase_attributes=self.codebase_attributes,
                        resource_attributes=self.resource_attributes)

    async def scan_files(self, single_scan: Scan, codebase: Codebase) -> Scan:
        async with MergeThread(codebase) as codebase:
            tasks = []
            async for single_file in single_scan.create_events():
                tasks.append(
                    self.scan_file(single_file, codebase.merge_result_for_resource)
                )
            await asyncio.gather(*tasks)
        return single_scan

    async def scan_file(self, single_file: ScanEvent, merge_func):
        assert single_file

        loop = asyncio.get_event_loop()
        tasks = []
        log.debug(f"File {single_file.relative_path} scan {single_file.uuid} requested for.")
        for _scan in self.scanners:
            task = loop.run_in_executor(self.executor, _scan, single_file.location)
            tasks.append(task)
        results = await asyncio.gather(*tasks)
        result = reduce(operator.ior, results, {})
        await merge_func(single_file.relative_path, result)


class MergeThread(Thread):
    def __init__(self, codebase: Codebase):
        super().__init__()
        self.codebase = codebase
        self.loop = asyncio.new_event_loop()

    async def write_result_for_resource(self, relative_path: str, result: dict):
        def merge(items, into):
            for k, v in items:
                if not v:
                    continue
                else:
                    setattr(into, k, v)

        log.debug(f"Merging result for '{relative_path}'")
        with_resource = self.codebase.get_resource(relative_path)
        merge(result.items(), with_resource)

        self.codebase.save_resource(with_resource)

    async def merge_result_for_resource(self, relative_path: str, result: dict):
        coro = self.write_result_for_resource(relative_path, result)
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        await asyncio.wrap_future(future)

    def run(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()
        self.loop.run_until_complete(asyncio.sleep(0))
        self.loop.close()

    async def internal_stop(self):
        self.loop.stop()

    async def stop(self):
        coro = self.internal_stop()
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        await asyncio.wrap_future(future)

    async def __aenter__(self):
        log.debug("Enter: Awaiting scan results for merging.")
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.start)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        log.debug("Exit: Stopping thread.")
        await self.stop()


@asynccontextmanager
async def lifespan(app: FastAPI):
    start = time.perf_counter()
    from licensedcode.cache import populate_cache
    populate_cache()
    log.info(f"Cache initialized. Time elapsed: {time.perf_counter() - start}")
    yield
    scan.shutdown()

app = FastAPI(lifespan=lifespan)
scan = AsynchronousScan()


class ScanRequest(BaseModel):
    scan_path: Path
    output_file: Path


@app.get("/scan")
async def status():
    scans = [task.uuid for task in scan.tasks]
    return {"status": "active", "scans": scans}


@app.post("/scan/")
async def scan_file(scan_request: ScanRequest) -> Any:
    uuid = await scan.execute(scan_request)
    scan_request_dict = scan_request.dict()
    scan_request_dict.update({"uuid": uuid})
    return scan_request_dict


def default_log_config():
    from importlib.resources import files
    return files('scancode_extensions.resources').joinpath('log_config.yaml')


@click.command()
@click.option('--workers', default=1, help="Number of parallel workers.")
@click.option('--log-config', default=default_log_config(), help="Configuration file for logging.")
@click.option('--port', default=8000, help="Port to accept connections.")
@click.option('--output_dir', help="Where to write output files.")
def start(log_config, workers, port, output_dir):
    uvicorn.run("scancode_extensions.service:app", host="0.0.0.0", port=port, workers=workers, log_config=log_config,
                timeout_graceful_shutdown=5)


if __name__ == "__main__":
    start()
