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

import dataclasses
import os.path
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import scancode_extensions
from scancode_extensions.service import app, scan

client = TestClient(app)


def test_get_returns_status():
    response = client.get("/scan")
    assert response.status_code == 200
    assert response.json()["status"] == "active"


class FakeScan:
    async def __call__(self, scan_request):
        return "Any_UUID"


@pytest.fixture
def replace_scan_singleton(monkeypatch):
    monkeypatch.setattr(scancode_extensions.service, "scan", FakeScan())


def test_post_requests_accepts_path_and_output_file(replace_scan_singleton):
    response = client.post("/scan/", json={"scan_path": "/home/kai/projekte/metaeffekt/scancode-toolkit/samples/",
                                           "output_file": "result.json"})
    assert response.status_code == 200


def test_post_returns_json_with_uuid(replace_scan_singleton):
    workload = {
        "scan_path": "/home/kai/projekte/metaeffekt/scancode-toolkit/samples/",
        "output_file": "result.json"
    }

    response = client.post("/scan/", json=workload)

    assert response.status_code == 200
    assert "uuid" in response.json()


@pytest.mark.parametrize("paths", ["/home/kai/projekte/metaeffekt/scancode-toolkit/samples/", ])
@pytest.mark.skip("Long running test.")
def test_multi_post(tmp_path, paths, faker):
    output_file = os.path.join(tmp_path, faker.file_name(extension="json"))

    for scan_path in paths:
        workload = {
            "scan_path": scan_path,
            "output_file": output_file
        }

        response = client.post("/scan/", json=workload)

        assert response.status_code == 200
        assert "uuid" in response.json()


@pytest.mark.parametrize("root", ["/home/kai/netty_intermediate/", ])
@pytest.mark.skip("Long running test.")
def test_multi_post_subfolder_scan(tmp_path, root, faker):
    output_file = os.path.join(tmp_path, faker.file_name(extension="json"))

    root = Path(root)
    for scan_path in root.iterdir():
        if os.path.isdir(scan_path):
            workload = {
                "scan_path": str(scan_path),
                "output_file": output_file
            }

            response = client.post("/scan/", json=workload)

            assert response.status_code == 200
            assert "uuid" in response.json()


@dataclasses.dataclass(frozen=True)
class FakeFuture:
    uuid: str

    def get_name(self):
        return self.uuid


def test_status_contains_list_of_active_scans(monkeypatch):
    monkeypatch.setattr(scancode_extensions.service, "tasks",
                        {FakeFuture("ID_01"), FakeFuture("ID_02"), FakeFuture("ID_03"), FakeFuture("ID_04"), })
    response = client.get("/scan")

    assert response.status_code == 200
    current_scans = response.json()['scans']
    assert all([id in current_scans for id in ['ID_01', 'ID_02', 'ID_03', 'ID_04']])
