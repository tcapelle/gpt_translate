from gpt_translate.utils import check_file_non_empty, split_markdown_file


def test_empty_file():
    "Check that the files are non empty"
    assert not check_file_non_empty("tests/data/empty.md")
    assert check_file_non_empty("tests/data/intro.md")


def test_split_markdown_file():
    "Check that splits work!"
    chunks = split_markdown_file("tests/data/intro.md", min_lines=10)
    assert len(chunks) == 3
    first_chunk_last_line = "<!-- ![](@site/static/images/general/diagram_2021.png) -->"
    assert chunks[0].split("\n")[-1] == first_chunk_last_line
    assert len(chunks[0].split("\n")) == 11

    second_chunk_last_line = "1. View the [API Reference guide](../ref/README.md) for technical specifications about the W&B Python Library, CLI, and Weave operations."
    assert chunks[1].split("\n")[-1] == second_chunk_last_line
    assert len(chunks[0].split("\n")) == 11

    last_chunk_last_line = "7. Organize W&B Runs, embed and automate visualizations, describe your findings, and share updates with collaborators with [Reports](./reports/intro.md)."
    assert chunks[2].split("\n")[-1] == last_chunk_last_line
