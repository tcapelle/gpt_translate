from gpt_translate.loader import (
    remove_markdown_comments,
    split_markdown,
    Header,
    extract_header,
)


def test_remove_markdown_comments():
    # Example usage with your Markdown content
    markdown_content = """
Some content
<!-- This is a comment
It spans multiple lines -->
More content
"""
    cleaned_content = remove_markdown_comments(markdown_content)

    assert (
        cleaned_content
        == """
Some content

More content
"""
    )


def test_split_markdown():
    # Example usage with your Markdown content
    markdown_content = """
Some pre-header content
# Header 1
Content under header 1
## Header 1.1
Content under header 1.1
# Header 2
Content under header 2
"""

    chunks = split_markdown(markdown_content)

    # no line breaks
    assert (
        chunks[2]
        == """## Header 1.1
Content under header 1.1"""
    )


def test_header():

    # test simple header
    page = """
---
description: description
slug: /guides/app
displayed_sidebar: default
---
# title
"""
    header = """---\ndescription: description\nslug: /guides/app\ndisplayed_sidebar: default\n---"""
    extracted_header = extract_header(page)["header"]
    assert extracted_header == header
    header_obj = Header.from_string(extracted_header)
    assert header_obj.description == "description"
    assert header_obj.displayed_sidebar == "default"
    assert header_obj.slug == "/guides/app"
    assert str(header_obj) == header

    # test import
    page = """
import 1;
import 2;
import 3;

# title
"""
    header = """import 1;\nimport 2;\nimport 3;"""
    extracted_header = extract_header(page)["header"]
    assert extracted_header == header
    header_obj = Header.from_string(extracted_header)
    assert header_obj.description == ""
    assert header_obj.displayed_sidebar == ""
    assert header_obj.slug == ""
    assert header_obj.imports == "import 1;\nimport 2;\nimport 3;"
    assert str(header_obj) == header

    # test import + header
    page = """
---
description: description
slug: /guides/app
displayed_sidebar: default
---

import 1;
import 2;
import 3;

# title
"""
    header = """---\ndescription: description\nslug: /guides/app\ndisplayed_sidebar: default\n---\n\nimport 1;\nimport 2;\nimport 3;"""
    extracted_header = extract_header(page)["header"]
    assert extracted_header == header
    header_obj = Header.from_string(extracted_header)
    assert header_obj.description == "description"
    assert header_obj.displayed_sidebar == "default"
    assert header_obj.slug == "/guides/app"
    assert header_obj.imports == "import 1;\nimport 2;\nimport 3;"
    assert str(header_obj) == header

    # test empty header
    page = """
# title
"""
    header = ""
    extracted_header = extract_header(page)["header"]
    assert extracted_header == header
    header_obj = Header.from_string(extracted_header)
    assert header_obj.description == ""
    assert header_obj.displayed_sidebar == ""
    assert header_obj.slug == ""
    assert header_obj.imports == ""
    assert str(header_obj) == header
