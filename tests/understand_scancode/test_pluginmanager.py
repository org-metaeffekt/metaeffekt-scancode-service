from dataclasses import dataclass

import pytest
from cluecode.plugin_copyright import CopyrightScanner
from commoncode.resource import Codebase
from formattedcode.output_json import JsonPrettyOutput
from licensedcode.plugin_license import LicenseScanner
from scancode.cli import ScancodeCodebase
from scancode.plugin_info import InfoScanner


def test_xxx():
    # these are important to register plugin managers
    from plugincode import PluginManager
    from plugincode import pre_scan
    from plugincode import scan
    from plugincode import post_scan
    from plugincode import output_filter
    from plugincode import output

    assert len(PluginManager.managers) == 5

    mgr: PluginManager
    for stage, mgr in PluginManager.managers.items():
        print(f"\n\t------\n\tSetup stage: {stage}")
        setup = mgr.setup()
        if setup:
            print(setup)


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
            "copyright": CopyrightScanner(),
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
        plugin.process_codebase(codebase)

    def test_output(self, codebase: Codebase, processed_resources):
        """Save results stored in the codebase into a json file."""
        plugin = JsonPrettyOutput()
        plugin.process_codebase(codebase, output_json_pp="test.json", info=True)
