import dataclasses
import logging
import multiprocessing as mp
import time

import pytest
from cluecode.plugin_copyright import CopyrightScanner
from scancode_extensions.resource import ScancodeCodebase as Codebase
from licensedcode.plugin_license import LicenseScanner
from scancode.plugin_info import InfoScanner

from scancode_extensions.service import AsynchronousScan
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


def test_xxx():
    with mp.Manager() as manager:
        shutdown_requested = manager.Event()
        p = mp.Process(target=printer, args=(shutdown_requested,))
        p.start()
        time.sleep(10)
        shutdown_requested.set()
        p.join()


@dataclasses.dataclass
class ScanFinished:
    uuid: str


@pytest.fixture(scope="class")
def populated_cache():
    from licensedcode.cache import populate_cache
    populate_cache()


@pytest.mark.asyncio
async def test_scanner_async(scan, populated_cache):
    # asyncio.get_event_loop().set_debug(True)
    # base = "/home/kai/netty_intermediate/[netty-all]"
    base = "/home/kai/projekte/metaeffekt/scancode-toolkit/samples"
    # base ="/home/kai/netty_intermediate"
    file = await scan.execute(base)
    assert "/tmp" in file


@pytest.mark.asyncio
async def test_scanner_async_with_many_small_files(scan, populated_cache, fifty_folders_each_contains_single_file):
    file = await scan.execute(fifty_folders_each_contains_single_file)
    assert "/tmp" in file


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
def test_os_walk():
    import os
    for root, dirs, files in os.walk("/home/kai/projekte/metaeffekt/scancode-toolkit/samples/", topdown=False):
        for name in files:
            print(os.path.join(root, name))


def test_codebase(sample_codebase):
    relpath = "samples/JGroups/licenses/bouncycastle.txt"
    resource = sample_codebase.get_resource(relpath)
    assert resource


@timings
def init_codebase(scan: AsynchronousScan, base, *args, **kwargs):
    log.info("Initialize codebase.")
    codebase = Codebase(base, codebase_attributes=scan.codebase_attributes,
                        resource_attributes=scan.resource_attributes, *args, **kwargs)
    codebase.get_or_create_current_header()
    log.info("Initialization completed.")
    return codebase


def test_build_codebase(scan, samples_folder):
    codebase = init_codebase(scan, samples_folder,
                             max_in_memory=10000, strip_root=False,
                             full_root=False, max_depth=0, )

    assert codebase.compute_counts() == (33, 11, 0)
