from pathlib import Path

from scancode_extensions.service import Scan


def test_init_scan():
    base = Path("/any/path")
    output_file = Path("/another/path/result.json")

    out = Scan(base, output_file)

    assert out.base == Path("/any/path")
    assert out.output_file == Path("/another/path/result.json")
