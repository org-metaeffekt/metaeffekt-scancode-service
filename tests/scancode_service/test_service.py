import asyncio
import dataclasses
import logging
import time

import pytest
import pytest_asyncio
from cluecode.plugin_copyright import CopyrightScanner
from licensedcode.plugin_license import LicenseScanner
from scancode.plugin_info import InfoScanner

from scancode_extensions import resource
from scancode_extensions.resource import ScancodeCodebase as Codebase
from scancode_extensions.service import ScanRequest, AsynchronousScan, Scan
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


@pytest.mark.asyncio
async def test_scanner_async(scan, populated_cache, samples_folder):
    await scan.execute(ScanRequest(scan_path=(samples_folder), output_file="/dev/null"))

    assert len(scan.tasks) == 1
    task = list(scan.tasks)[0]
    await asyncio.gather(*scan.tasks)
    assert task.done()


@pytest.mark.asyncio
async def test_scanner_async_with_many_small_files(scan, populated_cache, fifty_folders_each_contains_single_file):
    await scan.execute(ScanRequest(scan_path=str(fifty_folders_each_contains_single_file), output_file="/dev/null"))

    await asyncio.gather(*scan.tasks)


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
async def test_erroneous_task_stops_execution(scan_with_error, samples_folder, event_loop):
    event_loop.set_debug(True)
    scan, task = scan_with_error
    to_schedule = Scan(samples_folder, "/dev/null")
    await scan.schedule_scan(to_schedule)

    assert len(scan.tasks) == 1

    task.throw_error()
    with pytest.raises(RuntimeError):
        await asyncio.gather(*scan.tasks)


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
