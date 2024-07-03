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


def test_simple_header():
    header = """---
description: description
slug: /guides/app
displayed_sidebar: default
---"""
    content = """
# title
"""
    page = header + "\n" + content
    extracted_header = extract_header(page)["header"]
    assert extracted_header == header
    header_obj = Header.from_string(extracted_header)
    assert header_obj.description == "description"
    assert header_obj.displayed_sidebar == "default"
    assert header_obj.slug == "/guides/app"
    assert str(header_obj) == header


def test_header_with_imports():
    header = """import 1;
import 2;
import 3;"""
    content = """
# title
"""
    page = header + "\n" + content
    extracted_header = extract_header(page)["header"]
    assert extracted_header == header
    header_obj = Header.from_string(extracted_header)
    assert header_obj.description == None
    assert header_obj.displayed_sidebar == None
    assert header_obj.slug == None
    assert header_obj.imports == "import 1;\nimport 2;\nimport 3;"
    assert str(header_obj) == header


def test_header_with_frontmatter_and_imports():
    header = """---
description: description
slug: /guides/app
displayed_sidebar: default
---
import 1;
import 2;
import 3;"""
    content = """
# title
"""
    page = header + "\n" + content
    extracted_header = extract_header(page)["header"]
    assert extracted_header == header
    header_obj = Header.from_string(extracted_header)
    assert header_obj.description == "description"
    assert header_obj.displayed_sidebar == "default"
    assert header_obj.slug == "/guides/app"
    assert header_obj.imports == "import 1;\nimport 2;\nimport 3;"
    assert str(header_obj) == header


def test_empty_header():
    header = ""
    content = """
# title
"""
    page = header + "\n" + content
    extracted_header = extract_header(page)["header"]
    assert extracted_header == header
    header_obj = Header.from_string(extracted_header)
    assert header_obj.description == None
    assert header_obj.displayed_sidebar == None
    assert header_obj.slug == None
    assert header_obj.imports == None
    assert str(header_obj) == header


def test_header_with_title():
    header = """---
title: Install on on-prem infra
description: Hosting W&B Server on on-premises infrastructure
displayed_sidebar: default
---
import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';"""

    content = """:::info
W&B recommends fully managed deployment options such as [W&B Multi-tenant Cloud](../hosting-options/saas_cloud.md) or [W&B Dedicated Cloud](../hosting-options//dedicated_cloud.md) deployment types. W&B fully managed services are simple and secure to use, with minimum to no configuration required.
:::

You can run W&B Server on your on-premises infrastructure if Multi-tenant Cloud or Dedicated Cloud are not a good fit for your organization."""
    page = header + "\n" + content
    extracted = extract_header(page)
    assert extracted["header"] == header
    header_obj = Header.from_string(extracted["header"])
    assert header_obj.title == "Install on on-prem infra"
    assert header_obj.description == "Hosting W&B Server on on-premises infrastructure"
    assert header_obj.displayed_sidebar == "default"
    assert (
        header_obj.imports
        == "import Tabs from '@theme/Tabs';\nimport TabItem from '@theme/TabItem';"
    )
    assert str(header_obj) == header
    assert extracted["content"] == content


def test_header_serialization_with_japanese_characters():
    header_obj = Header(
        title="オンプレミス インフラストラクチャー",
        description="オンプレミス インフラストラクチャー上での W&B サーバーのホスティング",
        displayed_sidebar="default",
        imports="",
    )
    expected_header = """
---
title: オンプレミス インフラストラクチャー
description: オンプレミス インフラストラクチャー上での W&B サーバーのホスティング
displayed_sidebar: default
---
"""
    assert (
        header_obj.description
        == "オンプレミス インフラストラクチャー上での W&B サーバーのホスティング"
    )
    assert str(header_obj) == expected_header.strip()


def test_header_serialization_with_newlines_in_description():
    header_obj = Header(
        title="Sample Title",
        description="This is a description\nwith multiple lines\nthat should be serialized correctly.\n",
        displayed_sidebar="default",
        imports="",
    )
    expected_header = """
---
title: Sample Title
description: This is a description with multiple lines that should be serialized correctly.
displayed_sidebar: default
---
"""
    assert (
        header_obj.description
        == "This is a description\nwith multiple lines\nthat should be serialized correctly.\n"
    )
    assert str(header_obj) == expected_header.strip()


def test_header_class():
    "Empty header"
    h = Header(
        title=None, description=None, slug=None, displayed_sidebar=None, imports=None
    )
    assert str(h) == ""
