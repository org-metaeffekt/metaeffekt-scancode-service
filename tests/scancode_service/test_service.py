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
import time
from asyncio import BaseEventLoop

import pytest
import pytest_asyncio
from cluecode.plugin_copyright import CopyrightScanner
from licensedcode.plugin_license import LicenseScanner
from scancode.plugin_info import InfoScanner

from scancode_extensions import resource
from scancode_extensions import service
from scancode_extensions.resource import ScancodeCodebase as Codebase
from scancode_extensions.service import AsynchronousScan, ScanRequest, Scan
from scancode_extensions.utils import timings

log = logging.getLogger("scancodeservice-test")


def printer(shutdown_requested):
    start_time = time.perf_counter()
    while not shutdown_requested.is_set():
        current_time = time.perf_counter()
        run_time = current_time - start_time
        logging.warning(f"Still alive, working since {run_time}")
        time.sleep(2)
    logging.warning("Shutdown requested. Stopping.")


@dataclasses.dataclass
class ScanFinished:
    uuid: str


@pytest.fixture(scope="class")
def populated_cache():
    from licensedcode.cache import populate_cache
    populate_cache()


class ErroneousScan:
    def __init__(self):
        self.should_raise = False

    def __call__(self, *args, **kwargs):
        while True:
            if self.should_raise:
                raise RuntimeError

    def throw_error(self):
        self.should_raise = True


@pytest.mark.asyncio
async def test_erroneous_task_stops_execution(scan_with_error, samples_folder, codebase, event_loop: BaseEventLoop):
    scan, erroneous_task = scan_with_error
    to_schedule = Scan(samples_folder, "/dev/null")

    coro = scan.scan_files(to_schedule, codebase)
    future = event_loop.create_task(coro)

    erroneous_task.throw_error()
    with pytest.raises(RuntimeError):
        await future

@pytest_asyncio.fixture
async def scan_with_error() -> (AsynchronousScan, ErroneousScan):
    erroneous_scan = ErroneousScan()
    scan = AsynchronousScan(scanners=[erroneous_scan])
    return scan, erroneous_scan


@pytest.fixture(scope="class")
def plugins():
    """These are the plugins we need to get the desired output. Mostly equal to calling 'scancode -cli' on
    commandline.
    """
    return {
        "info": InfoScanner(),
        "copyright": CopyrightScanner(),
        "license": LicenseScanner(),
    }


@timings
def test_os_walk(samples_folder):
    import os
    for root, dirs, files in os.walk(samples_folder, topdown=False):
        for name in files:
            print(os.path.join(root, name))


def test_get_resource_from_codebase(sample_codebase):
    existing_path = "samples/JGroups/licenses/bouncycastle.txt"
    assert sample_codebase.get_resource(existing_path)
    non_existing_path = "xxx/this/path/is/not/existing"
    assert not sample_codebase.get_resource(non_existing_path)


@timings
def init_codebase(base, *args, **kwargs):
    log.info("Initialize codebase.")
    codebase = Codebase(base, codebase_attributes=resource.codebase_attributes(),
                        resource_attributes=resource.resource_attributes(), *args, **kwargs)
    codebase.get_or_create_current_header()
    log.info("Initialization completed.")
    return codebase


def test_build_codebase(samples_folder):
    codebase = init_codebase(samples_folder,
                             max_in_memory=10000, strip_root=False,
                             full_root=False, max_depth=0, )

    assert codebase.compute_counts() == (33, 11, 0)


async def fake_scan(self, *args, **kwargs):
    await asyncio.sleep(5)


@pytest.mark.asyncio
@pytest.mark.skip("Tasks are deleted 30s after finishing. Should not be awaited.")
async def test_read_status_of_scheduled_task():
    single_scan = Scan("/any/path", "any_output.json")
    await service.schedule_scan(single_scan, default_scan=fake_scan)

    assert service.get_task_status(single_scan.uuid) == dict(uuid=str(single_scan.uuid), status="pending")

    await list(service.tasks)[0]

    assert service.get_task_status(single_scan.uuid) == dict(uuid=str(single_scan.uuid), status="done")
    await asyncio.sleep(5)
    assert len(service.tasks) == 0
    with pytest.raises(KeyError):
        service.get_task_status(single_scan.uuid)
