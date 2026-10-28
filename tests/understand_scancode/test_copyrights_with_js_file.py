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
import datetime
import tempfile
from dataclasses import dataclass
from pathlib import Path
from time import time

import pytest
from commoncode.resource import Codebase
from formattedcode.output_json import JsonPrettyOutput
from licensedcode.plugin_license import LicenseScanner
from scancode.plugin_info import InfoScanner

from scancode_extensions import resource
from scancode_extensions.allrights_plugin import AllrightsCopyrightScanner
from scancode_extensions.resource import ScancodeCodebase
from scancode_extensions.resource import ScancodeCodebase as Codebase
from scancode_extensions.task_monitor import TaskInfo


@dataclass
class Location:
    location: str
    path: str


def merge(result, with_resource):
    for k, v in result.items():
        if not v:
            continue
        else:
            setattr(with_resource, k, v)


class TestFindPluginsNeeded:

    @pytest.fixture(scope="class")
    def codebase(self):
        return Codebase(
            Path("/Users/khammerschmidt/Downloads/brotli/brotli-1.0.6/js/decode.js"),
            # Path("/Users/khammerschmidt/Downloads/brotli/brotli-1.0.6/js/test_decode.js"),
            codebase_attributes=resource.codebase_attributes(),
            resource_attributes=resource.resource_attributes(),
        )

    @pytest.fixture(scope="class")
    def plugins(self):
        """These are the plugins we need to get the desired output. Mostly equal to calling 'scancode -cli' on
        commandline.
        """
        return {
            "info": InfoScanner(),
            "copyright": AllrightsCopyrightScanner(),
            "license": LicenseScanner(),
        }

    @pytest.fixture
    def save_codebase_counts(self, codebase: ScancodeCodebase):
        codebase.save_initial_counts()
        yield codebase
        codebase.save_final_counts(skip_root=False)

    @pytest.mark.parametrize("process", ["info", "copyright", "license"])
    def test_run_plugin(self, process, save_codebase_counts: ScancodeCodebase, plugins, build_cache, resources):
        """Run plugins one by one."""
        runner = plugins[process].get_scanner()
        scans = ((runner, Location(r.location, r.path)) for r in save_codebase_counts.walk() if r.is_file)

        resources: dict
        for func, location in scans:
            deadline = int(time() + 0.5)
            result = func(location.location, deadline=deadline)
            resources[location.path].update(result)

    @pytest.fixture(scope="class")
    def processed_resources(self, codebase, resources):
        """Process the collected results from resources dict and save these into codebase."""
        for path, results in resources.items():
            current_resource = codebase.get_resource(path)
            merge(results, current_resource)
            codebase.save_resource(current_resource)

    def test_update_detected_licenses(self, codebase: Codebase, processed_resources):
        plugin = LicenseScanner()
        plugin.process_codebase(codebase, license_diagnostics=False)

    def test_output(self, codebase: Codebase, processed_resources, tmp_path):
        """Save results stored in the codebase into a json file."""
        output_file = tempfile.mktemp(dir=tmp_path)
        plugin = JsonPrettyOutput()
        plugin.process_codebase(codebase, output_json_pp=output_file)

        found = {"base_name": False, "copyrights": False}
        with open(output_file) as f:
            for line in f.readlines():
                for k in found:
                    found[k] = found[k] or k in line
                if all(found.values()): break

        assert all(found.values())
        print(f"{output_file}")


def test_dict():
    d = {"1234": TaskInfo("uuid", datetime.datetime.now(), "location", "rel_path")}
    for k in list(d.keys()):
        if d[k].uuid == "uuid":
            print(f"found {k}\n")
            print(f"{k}: {d[k]}")
            del d[k]
    print(f"{d}")
