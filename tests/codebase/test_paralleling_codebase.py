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

import pytest
import pytest_asyncio

from scancode_extensions.resource import ScancodeCodebase as Codebase
from scancode_extensions.service import MergeThread


@pytest.mark.asyncio
async def test_written_result_can_be_read_from_codebase(samples_folder: str, sample_codebase):
    async with MergeThread(sample_codebase) as thread:
        resource_path: str = "samples/JGroups/LICENSE"
        result: dict = {"license_detections": [{
            "license_expression": "lgpl-2.1"
        }]}
        await thread.write(resource_path, result)

    out = sample_codebase.get_resource(resource_path).to_dict(with_info=True)
    assert "license_detections" in out
    assert out["name"] == "LICENSE"


@pytest.mark.asyncio
async def test_can_be_started_and_stopped(thread: MergeThread):
    thread.start()

    assert thread.is_alive()
    await thread.stop()
    thread.join()
    assert not thread.is_alive()


@pytest.mark.asyncio
async def test_use_in_context_manager(thread: MergeThread):
    async with thread:
        assert thread.is_alive()

    thread.join()
    assert not thread.is_alive()


@pytest.mark.asyncio
async def test_allow_async_merge(thread: MergeThread, sample_codebase: Codebase):
    async with thread as cb:
        await cb.write("samples/JGroups/LICENSE", {"license_detections": []})
        resource_dict = thread.codebase.get_resource("samples/JGroups/LICENSE").to_dict(with_info=True)

    assert "license_detections" in resource_dict
    second_dict = sample_codebase.get_resource("samples/JGroups/LICENSE").to_dict()
    assert "license_detections" in second_dict


@pytest_asyncio.fixture()
async def thread(sample_codebase: Codebase):
    thread = MergeThread(sample_codebase)
    yield thread
    if thread.is_alive():
        thread.stop()
