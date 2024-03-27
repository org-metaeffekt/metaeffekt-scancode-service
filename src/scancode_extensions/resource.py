import functools

from cluecode.plugin_copyright import CopyrightScanner
from commoncode.resource import Codebase
from licensedcode.plugin_license import LicenseScanner
from scancode.plugin_info import InfoScanner

from scancode_extensions.utils import timings


class ScancodeCodebase(Codebase):
    def __init__(self, *args, with_info=True, **kwargs, ):
        self.with_info = with_info
        super().__init__(*args, **kwargs, )

    def save_initial_counts(self):
        files_count, dirs_count, size_count = self.compute_counts()
        self.save_counts('initial', dirs_count, files_count, size_count)

    def save_final_counts(self, strip_root):
        files_count, dirs_count, size_count = self.compute_counts(skip_root=strip_root, skip_filtered=True)
        self.save_counts('final', dirs_count, files_count, size_count)

    def save_counts(self, phase, dirs_count, files_count, size_count):
        self.counters[('%s:files_count' % phase)] = files_count
        self.counters[('%s:dirs_count' % phase)] = dirs_count
        self.counters[('%s:size_count' % phase)] = size_count

    @functools.cache
    def _load_resource(self, path):
        return super()._load_resource(path)


plugins = [InfoScanner, CopyrightScanner, LicenseScanner, ]


def resource_attributes():
    attributes = {}
    for plugin in plugins:
        attributes.update(plugin.resource_attributes)
    return attributes


def codebase_attributes():
    attributes = {}
    for plugin in plugins:
        attributes.update(plugin.codebase_attributes)
    return attributes


@timings
async def create_codebase(base):
    return ScancodeCodebase(location=base, codebase_attributes=codebase_attributes(),
                            resource_attributes=resource_attributes())
