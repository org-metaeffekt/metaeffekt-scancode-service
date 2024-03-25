import os
from collections import defaultdict
from pathlib import Path

import pytest
from _pytest.fixtures import FixtureRequest
from scancode_extensions.resource import ScancodeCodebase as Codebase
from faker_file.providers.txt_file import TxtFileProvider
from faker_file.storages.filesystem import FileSystemStorage

from scancode_extensions.service import AsynchronousScan


@pytest.fixture(scope="class")
def scan():
    return AsynchronousScan()


@pytest.fixture(scope="class")
def codebase(scan) -> Codebase:
    return Codebase(
        "/home/kai/projekte/metaeffekt/scancode-toolkit/samples/",
        codebase_attributes=scan.codebase_attributes,
        resource_attributes=scan.resource_attributes,
    )


@pytest.fixture(scope="class")
def build_cache():
    from licensedcode.cache import populate_cache
    populate_cache()


@pytest.fixture(scope="class")
def resources():
    return defaultdict(dict)


@pytest.fixture(autouse=True)
def faker_locale():
    return ['de_DE']


@pytest.fixture(autouse=True)
def add_providers(faker):
    faker.add_provider(TxtFileProvider)


@pytest.fixture
def fifty_folders_each_contains_single_file(faker, add_providers, tmp_path):
    folders = [faker.file_path(depth=3, absolute=False) for _ in range(50)]
    for folder in folders:
        faker.txt_file(storage=FileSystemStorage(tmp_path, rel_path=folder))
    return tmp_path


@pytest.fixture
def sample_codebase(samples_folder):
    codebase = Codebase(samples_folder, with_info=True)
    return codebase


@pytest.fixture
def samples_folder(toolkit_base):
    return Path(toolkit_base, "samples")


@pytest.fixture()
def toolkit_base(request: FixtureRequest):
    return os.path.join(request.config.rootpath, "../scancode-toolkit")
