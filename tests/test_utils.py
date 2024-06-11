from gpt_translate.utils import file_is_empty, get_md_files


def test_empty_file():
    "Check that the files are non empty"
    assert file_is_empty("tests/data/empty.md")
    assert not file_is_empty("tests/data/intro.md")


def test_get_md_files():
    "Check that we get the right files"
    files = get_md_files("tests/data")
    assert len(files) == 2
    assert files[0].name == "empty.md"

    # Check that we can get a single file
    file = get_md_files("tests/data/intro.md")
    assert len(file) == 1

    # Check that we can get a single file with a glob
    none_files = get_md_files("tests/data", files_glob="*.txt")
    assert len(none_files) == 0

    # Check that we can get a single file with a regex
    file_re = get_md_files("tests/data", file_re="intro")
    assert len(file_re) == 1
