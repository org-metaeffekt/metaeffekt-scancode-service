def test_create_50_files_and_folders(fifty_folders_each_contains_single_file):
    assert len(list(fifty_folders_each_contains_single_file.iterdir())) == 50

