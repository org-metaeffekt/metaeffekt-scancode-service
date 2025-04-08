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

import tempfile

from formattedcode.output_json import write_results

from scancode_extensions.resource import ScancodeCodebase


def test_use_with_info_adds_basenames(samples_folder, tmp_path):
    base = ScancodeCodebase(samples_folder)

    output_file = tempfile.mktemp(dir=tmp_path)
    write_results(base, output_file)

    with open(output_file) as f:
        for line in f.readlines():
            found = "base_name" in line
            if found: break

    assert found
