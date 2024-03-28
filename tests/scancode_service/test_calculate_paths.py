from pathlib import Path

from scancode_extensions.service import Scan
from scancode_extensions.utils import compute_scanroot_relative


def test_calculate():
    scan_root = "/tmp/netty_intermediate"
    rel_root = str(Path(scan_root).parent)

    assert rel_root == "/tmp"


def test_generate_scancode_relative():
    scan_root = "/tmp/netty_intermediate"
    any_file = "/tmp/netty_intermediate/[netty-all]/[netty-all-4.1.68.Final.jar-3ae6177fe4f5fd30fee41997cb93fef0]-intermediate/META-INF/MANIFEST.MF/segment-0.txt"

    relative = compute_scanroot_relative(any_file, scan_root)

    assert relative == "netty_intermediate/[netty-all]/[netty-all-4.1.68.Final.jar-3ae6177fe4f5fd30fee41997cb93fef0]-intermediate/META-INF/MANIFEST.MF/segment-0.txt"


def test_init_scan():
    base = Path("/any/path")
    output_file = Path("/another/path/result.json")

    out = Scan(base, output_file)

    assert out.base == Path("/any/path")
    assert out.output_file == Path("/another/path/result.json")
