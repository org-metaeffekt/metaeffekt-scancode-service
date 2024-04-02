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
from typing import Any, Callable

import click
import uvicorn
from fastapi import FastAPI
from formattedcode.output_json import JsonPrettyOutput
from pydantic import BaseModel
from scancode.api import get_licenses, get_file_info

from scancode_extensions import resource
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

    def __init__(self, scanners: list[Callable] = None):
        number_processes = 12
        self.executor = ProcessPoolExecutor(number_processes)
        self.thread_executor = ThreadPoolExecutor(2)
        if not scanners:
            self.scanners = [get_file_info, get_licenses, allrights_scanner]
        else:
            self.scanners = scanners

    def shutdown(self):
        log.error("Shutdown executor.")
        self.executor.shutdown(cancel_futures=True)

    def write_json(self, json_file: Path, codebase: Codebase) -> None:
        plugin = JsonPrettyOutput()
        runner = timings(partial(plugin.process_codebase, output_json_pp=str(json_file), info=True, codebase=codebase))
        self.thread_executor.submit(runner)

    async def __call__(self, single_scan: Scan) -> None:
        start = time.perf_counter()
        codebase = await resource.create_codebase(single_scan.base)
        await self.scan_files(single_scan, codebase)
        self.write_json(single_scan.output_file, codebase)
        log.warning(f"Scan with uuid {single_scan.uuid} has total scan time: {time.perf_counter() - start}")

    async def scan_files(self, single_scan: Scan, codebase: Codebase) -> None:
        async with MergeThread(codebase) as codebase:
            tasks = []
            async for single_file in single_scan.create_events():
                tasks.append(
                    self.scan_file(single_file, codebase.write)
                )
            await asyncio.gather(*tasks)

    async def scan_file(self, single_file: ScanEvent, write):
        log.debug(f"File {single_file.relative_path} scan {single_file.uuid} requested for.")

        loop = asyncio.get_event_loop()
        tasks = []
        for _scan in self.scanners:
            task = loop.run_in_executor(self.executor, _scan, single_file.location)
            tasks.append(task)
        results = await asyncio.gather(*tasks)
        result = reduce(operator.ior, results, {})
        await write(single_file.relative_path, result)


class MergeThread(Thread):
    def __init__(self, codebase: Codebase):
        super().__init__()
        self.codebase = codebase
        self.loop = asyncio.new_event_loop()

    async def _write(self, at: str, result: dict):
        def merge(items, into):
            for k, v in items:
                if not v:
                    continue
                else:
                    setattr(into, k, v)

        log.debug(f"Merging result for '{at}'")
        with_resource = self.codebase.get_resource(at)
        merge(result.items(), with_resource)

        self.codebase.save_resource(with_resource)

    async def write(self, resource_path: str, result: dict):
        coro = self._write(resource_path, result)
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


tasks = set()

app = FastAPI(lifespan=lifespan)
scan = AsynchronousScan()


async def execute(scan_request: "ScanRequest"):
    single_scan = Scan(scan_request.scan_path, scan_request.output_file)
    log.info(f"Scan with uuid {single_scan.uuid}: Scanning dir {single_scan.base}.")
    await schedule_scan(single_scan)
    return single_scan.uuid


async def schedule_scan(single_scan, default_scan=None):
    if not default_scan:
        default_scan = scan
    coro = default_scan(single_scan)
    name = str(single_scan.uuid)
    await schedule_task(coro, name)


async def schedule_task(coro, name):
    def discard(fut):
        async def coro():
            await asyncio.sleep(30)
            tasks.discard(fut)

        asyncio.create_task(coro())

    future = asyncio.create_task(coro, name=name)
    future.add_done_callback(discard)
    tasks.add(future)


class ScanRequest(BaseModel):
    scan_path: Path
    output_file: Path


@app.get("/scan")
async def status():
    scans = [task.get_name() for task in tasks]
    return {"status": "active", "scans": scans}


def get_task_status(uuid):
    uuid = str(uuid)
    task_dict = {task.get_name(): task for task in tasks}
    task = task_dict[uuid]
    return dict(uuid=uuid, status="done" if task.done() else "pending")


@app.get("/scan/{uuid}")
async def status(uuid: str):
    status_dict = get_task_status(uuid)
    return status_dict


@app.post("/scan/")
async def scan_file(scan_request: ScanRequest) -> Any:
    uuid = await execute(scan_request)
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
