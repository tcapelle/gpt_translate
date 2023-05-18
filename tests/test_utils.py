from gpt_translate.utils import check_file_non_empty


def test_empty_file():
    "Check that the files are non empty"
    assert not check_file_non_empty("tests/data/empty.md")
    assert check_file_non_empty("tests/data/intro.md")
