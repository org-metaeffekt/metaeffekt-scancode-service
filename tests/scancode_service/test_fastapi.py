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
    async def execute(self, scan_request):
        return "Any_UUID"


@pytest.fixture
def replace_scan_singleton(monkeypatch):
    monkeypatch.setattr(scancode_extensions.service, "scan", FakeScan())


def test_post_requests_accepts_path_and_output_file(replace_scan_singleton, samples_folder):
    response = client.post("/scan/", json={"scan_path": f"{samples_folder}",
                                           "output_file": "result.json"})
    assert response.status_code == 200


def test_post_returns_json_with_uuid(replace_scan_singleton, samples_folder):
    workload = {
        "scan_path": f"{samples_folder}",
        "output_file": "result.json"
    }

    response = client.post("/scan/", json=workload)

    assert response.status_code == 200
    assert response.json()["uuid"] == "Any_UUID"


@pytest.mark.skip("Long running test.")
@pytest.mark.asyncio
def test_multi_post(tmp_path, samples_folder, faker):
    paths = [samples_folder]
    output_file = os.path.join(tmp_path, faker.file_name(extension="json"))

    for scan_path in paths:
        workload = {
            "scan_path": f"{scan_path}",
            "output_file": output_file
        }

        response = client.post("/scan/", json=workload)

        assert response.status_code == 200
        assert "uuid" in response.json()


@pytest.mark.parametrize("root", ["/tmp/netty_intermediate/", ])
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


@dataclasses.dataclass
class FakeFuture:
    uuid: str


def test_status_contains_list_of_active_scans(monkeypatch):
    monkeypatch.setattr(scan, "tasks",
                        [FakeFuture("ID_01"), FakeFuture("ID_02"), FakeFuture("ID_03"), FakeFuture("ID_04"), ])
    response = client.get("/scan")

    assert response.status_code == 200
    assert response.json()['scans'] == ['ID_01', 'ID_02', 'ID_03', 'ID_04']
