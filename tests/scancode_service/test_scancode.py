from typing import Any

import pytest
from cluecode.plugin_copyright import CopyrightScanner

from scancode_extensions.service import AsynchronousScan


class ResourceMappingRunner:

    def __init__(self, function) -> None:
        self.function = function

    def __call__(self, *args: Any, **kwds: Any) -> Any:
        location, path = args[0]
        # print(f"location: {location}, path: {path}")
        return self.function(location)


def test_make_copyright_plugin_work(codebase):
    plugin = CopyrightScanner()

    runner = ResourceMappingRunner(plugin.get_scanner())
    scans = ((runner, (r.location, r.path)) for r in codebase.walk() if r.is_file)

    for func, args in scans:
        result = func(args)
        print(f"{args[0]} -> {result}")


@pytest.fixture(scope="class")
def scan():
    return AsynchronousScan()

