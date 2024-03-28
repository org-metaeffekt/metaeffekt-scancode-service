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
