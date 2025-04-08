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

from functools import partial
from pathlib import Path

from scancode_extensions.utils import make_atomic


def test_enter_scenario():
    output_json = Path("/tmp/json/out.put")

    def like_process_codebase(output_json_pp: str):
        assert output_json_pp == "/tmp/json/out.put"

    like_process_codebase(str(output_json))


def test_wrap_that_call():
    output_json = Path("/tmp/json/out.put")

    def like_process_codebase(output_json_pp: str):
        assert output_json_pp == "/tmp/json/out.put"

    make_atomic(like_process_codebase)(str(output_json))


def test_modify_output_json_pp(tmp_path):
    output_json = Path(tmp_path, "out.put")
    output_json.touch()

    def like_process_codebase(output_json_pp: str):
        Path(output_json_pp).touch()
        assert output_json_pp == f"{tmp_path}/out.put.modified.tmp"

    make_atomic(like_process_codebase, modifier=lambda: "modified")(output_json_pp=str(output_json))


def test_with_partial(tmp_path):
    output_json = Path(tmp_path, "out.put")
    output_json.touch()

    def like_process_codebase(output_json_pp: str):
        Path(output_json_pp).touch()
        assert output_json_pp == f"{tmp_path}/out.put.modified.tmp"

    # Be careful: partial must wrap make_atomic.
    partial(make_atomic(like_process_codebase, modifier=lambda: "modified"), output_json_pp=str(output_json))()
