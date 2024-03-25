import tempfile
from dataclasses import dataclass

import pytest
from commoncode.resource import Codebase
from formattedcode.output_json import JsonPrettyOutput
from licensedcode.plugin_license import LicenseScanner
from scancode_extensions.resource import ScancodeCodebase
from scancode.plugin_info import InfoScanner

from scancode_extensions.allrights_plugin import AllrightsCopyrightScanner


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
        codebase.save_final_counts(strip_root=False)

    @pytest.mark.parametrize("process", ["info", "copyright", "license"])
    def test_run_plugin(self, process, save_codebase_counts: ScancodeCodebase, plugins, build_cache, resources):
        """Run plugins one by one."""
        runner = plugins[process].get_scanner()
        scans = ((runner, Location(r.location, r.path)) for r in save_codebase_counts.walk() if r.is_file)

        resources: dict
        for func, location in scans:
            result = func(location.location)
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

        found = {"base_name": False, "All rights": False}
        with open(output_file) as f:
            for line in f.readlines():
                for k in found:
                    found[k] = found[k] or k in line
                if all(found.values()): break

        assert all(found.values())
        print(f"{output_file}")
