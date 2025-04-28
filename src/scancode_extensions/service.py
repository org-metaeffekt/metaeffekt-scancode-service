#  Copyright 2021-2025 the original author or authors.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

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

from commoncode.resource import skip_ignored
from commoncode.timeutils import time2tstamp
from fastapi import FastAPI, HTTPException
from formattedcode.output_json import JsonPrettyOutput
from licensedcode.plugin_license import LicenseScanner
from pydantic import BaseModel
from scancode.api import get_licenses, get_file_info
from starlette.concurrency import run_in_threadpool

from scancode_extensions import resource
from scancode_extensions.allrights_plugin import allrights_scanner
from scancode_extensions.config import settings
from scancode_extensions.resource import ScancodeCodebase as Codebase
from scancode_extensions.utils import compute_scanroot_relative, timings, make_atomic

log = logging.getLogger("scanservice")

scancode_config = dict(output_dir="/tmp")


@dataclasses.dataclass
class Scan:
    base: str
    output_file: str
    uuid: uuid = field(init=False, default_factory=uuid.uuid4)

    async def create_events(self):
        for _root, dirs, files in os.walk(self.base, topdown=False):
            for name in files:
                full_path = os.path.join(_root, name)
                if skip_ignored(full_path):
                    continue
                yield ScanEvent(uuid=self.uuid, location=full_path,
                                relative_path=compute_scanroot_relative(full_path, self.base))


@dataclasses.dataclass
class FileScan(Scan):

    async def create_events(self):
        yield ScanEvent(uuid=self.uuid, location=str(self.base),
                        relative_path=compute_scanroot_relative(self.base, self.base))


@dataclasses.dataclass
class ScanEvent:
    uuid: str
    location: str
    relative_path: str


class AsynchronousScan:

    def __init__(self, scanners: list[Callable] = None, processes: int = 6, delta_t: int = 10):
        log.info(f"Configuring number of processes to: {processes}.")
        log.info(f"Configuring delta_t for scan deadlines to: {delta_t}.")
        self.executor = ProcessPoolExecutor(processes)
        self.thread_executor = ThreadPoolExecutor(2)
        self.delta_t = delta_t
        if not scanners:
            self.scanners = [get_file_info, get_licenses, allrights_scanner]
        else:
            self.scanners = scanners

    def shutdown(self):
        log.error("Shutdown executor.")
        self.executor.shutdown(cancel_futures=True)

    def write_json(self, json_file: Path, codebase: Codebase) -> None:
        plugin = JsonPrettyOutput()
        runner = timings(
            partial(make_atomic(plugin.process_codebase), output_json_pp=str(json_file), info=True, codebase=codebase))
        self.thread_executor.submit(runner)

    async def __call__(self, single_scan: Scan) -> None:
        start = time.perf_counter()
        start_time = time2tstamp()
        codebase = await run_in_threadpool(resource.create_codebase, single_scan.base)
        await self.scan_files(single_scan, codebase)
        codebase.update_header(start_timestamp=start_time, end_timestamp=time2tstamp(),
                               duration=time.perf_counter() - start,
                               options=dict(base=str(single_scan.base), output_file=str(single_scan.output_file)))
        await self.add_license_detections(codebase)
        self.write_json(single_scan.output_file, codebase)
        log.info(f"Scan with uuid {single_scan.uuid} has total scan time: {time.perf_counter() - start}")

    @staticmethod
    async def add_license_detections(codebase):
        LicenseScanner().process_codebase(codebase, license_text=True, license_diagnostics=True,
                                          license_text_diagnostics=True)

    async def scan_files(self, single_scan: Scan, codebase: Codebase) -> None:
        async with MergeThread(codebase) as codebase:
            async with asyncio.TaskGroup() as tg:
                async for single_file in single_scan.create_events():
                        tg.create_task(self.scan_file(single_file, codebase.write))

    async def scan_file(self, single_file: ScanEvent, write):
        log.debug(f"File {single_file.relative_path} scan {single_file.uuid} requested for.")

        loop = asyncio.get_event_loop()
        single_file_task = [loop.run_in_executor(self.executor, partial(_scan, deadline=self.calculate_deadline()), single_file.location) for _scan in self.scanners]
        results = await asyncio.gather(*single_file_task)
        result = reduce(operator.ior, results, {})
        await write(single_file.relative_path, result)

    def calculate_deadline(self):
        return time.time() + int(self.delta_t)


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
        if not with_resource:
            log.warning(f"Resource for {at} not found. Result is: {result.items()}")

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
scan = AsynchronousScan(processes=settings.processes, delta_t=settings.delta_t)


async def execute(scan_request: "ScanRequest"):
    scan_path = scan_request.scan_path
    output_file = scan_request.output_file
    if os.path.isfile(scan_path):
        single_scan = FileScan(scan_path, output_file)
        log.info(f"Scan with uuid {single_scan.uuid}: Scanning file {single_scan.base}.")
    elif os.path.isdir(scan_path):
        single_scan = Scan(scan_path, output_file)
        log.info(f"Scan with uuid {single_scan.uuid}: Scanning dir {single_scan.base}.")
    else:
        raise HTTPException(400, f"File or directory '{scan_path}' of variable 'scan_path' not found.")
    log.info(f"Writing scan result for {single_scan.uuid} into {single_scan.output_file}.")
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
    if uuid not in task_dict:
        raise HTTPException(status_code=404, detail="UUID not found")
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
