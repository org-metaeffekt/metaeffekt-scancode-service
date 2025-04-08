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

import functools
import scancode_config

from cluecode.plugin_copyright import CopyrightScanner
from commoncode.resource import Codebase
from licensedcode.plugin_license import LicenseScanner
from scancode.plugin_info import InfoScanner

from scancode_extensions.utils import timings, get_system_environment


class ScancodeCodebase(Codebase):
    def __init__(self, *args, with_info=True, **kwargs, ):
        self.with_info = with_info
        super().__init__(*args, **kwargs, )

    def save_initial_counts(self):
        files_count, dirs_count, size_count = self.compute_counts()
        self.save_counts('initial', dirs_count, files_count, size_count)

    def save_final_counts(self, skip_root):
        files_count, dirs_count, size_count = self.compute_counts(skip_root=skip_root, skip_filtered=True)
        self.save_counts('final', dirs_count, files_count, size_count)

    def save_counts(self, phase, dirs_count, files_count, size_count):
        self.counters[('%s:files_count' % phase)] = files_count
        self.counters[('%s:dirs_count' % phase)] = dirs_count
        self.counters[('%s:size_count' % phase)] = size_count

    def update_header(self, **kwargs):
        cle = self.get_or_create_current_header()
        cle.start_timestamp = kwargs.get("start_timestamp")
        cle.end_timestamp = kwargs.get("end_timestamp")
        cle.duration = kwargs.get("duration")
        cle.tool_name = 'scancode-toolkit'
        cle.tool_version = scancode_config.__version__
        cle.output_format_version = scancode_config.__output_format_version__
        cle.notice = "Executed within scancode-service."
        cle.options = kwargs.get("options")
        # useful for debugging
        cle.extra_data['system_environment'] = get_system_environment()
        self.save_final_counts(skip_root=False)
        self.add_files_count_to_current_header()

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
def create_codebase(base):
    codebase = ScancodeCodebase(location=base, codebase_attributes=codebase_attributes(),
                                resource_attributes=resource_attributes())
    codebase.save_initial_counts()
    return codebase
