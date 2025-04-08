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

import os
from collections import defaultdict
from pathlib import Path

import pytest
from _pytest.fixtures import FixtureRequest
from faker_file.providers.txt_file import TxtFileProvider
from faker_file.storages.filesystem import FileSystemStorage

from scancode_extensions import resource
from scancode_extensions.resource import ScancodeCodebase as Codebase
from scancode_extensions.service import AsynchronousScan


@pytest.fixture(scope="class")
def scan():
    return AsynchronousScan()


@pytest.fixture(scope="class")
def codebase(scan, samples_folder) -> Codebase:
    return Codebase(
        samples_folder,
        codebase_attributes=resource.codebase_attributes(),
        resource_attributes=resource.resource_attributes(),
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
    codebase = Codebase(samples_folder, resource_attributes=resource.resource_attributes(),
                        codebase_attributes=resource.codebase_attributes(), with_info=True)
    return codebase


@pytest.fixture(scope="session")
def samples_folder(toolkit_base):
    return Path(toolkit_base, "samples")


@pytest.fixture(scope="session")
def toolkit_base(request: FixtureRequest):
    """Points to scancode toolkits folder. Must be a sibling of project directory."""
    toolkit_base = os.path.join(request.config.rootpath, "../scancode-toolkit")
    if not os.path.exists(toolkit_base):
        raise FileNotFoundError("ScanCode Toolkit is not a sibling of project directory.")
    return toolkit_base
