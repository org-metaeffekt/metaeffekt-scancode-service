import pytest
import pytest_asyncio

from scancode_extensions import resource
from scancode_extensions.resource import ScancodeCodebase as Codebase

from scancode_extensions.service import MergeThread


@pytest.mark.skip
def test_xxx(base: str):
    codebase = Codebase(base)
    thread = MergeThread(codebase)
    relative_path: str = "samples/JGroups/LICENSE"
    result: dict = {"license_detections": []}
    thread._write(relative_path, result)

    resource_dict = codebase.get_resource(relative_path).to_dict(with_info=True)
    assert "license_detections" in resource_dict
    assert resource_dict["name"] == "abc.txt"


@pytest.mark.asyncio
async def test_can_be_started_and_stopped(thread: MergeThread):
    thread.start()

    assert thread.is_alive()
    await thread.stop()
    thread.join()
    assert not thread.is_alive()


@pytest.mark.asyncio
async def test_use_in_context_manager(thread: MergeThread):
    async with thread as codebase:
        assert thread.is_alive()

    thread.join()
    assert not thread.is_alive()


@pytest.mark.asyncio
async def test_allow_async_merge(thread: MergeThread, codebase: Codebase):
    async with thread as cb:
        await cb.write("samples/JGroups/LICENSE", {"license_detections": []})
        resource_dict = thread.codebase.get_resource("samples/JGroups/LICENSE").to_dict(with_info=True)

    assert "license_detections" in resource_dict
    second_dict = codebase.get_resource("samples/JGroups/LICENSE").to_dict()
    assert "license_detections" in second_dict


@pytest_asyncio.fixture()
async def thread(codebase: Codebase):
    thread = MergeThread(codebase)
    yield thread
    if thread.is_alive():
        thread.stop()


@pytest_asyncio.fixture()
async def codebase(samples_folder, scan):
    return Codebase(samples_folder, resource.codebase_attributes(), resource.resource_attributes())
