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
