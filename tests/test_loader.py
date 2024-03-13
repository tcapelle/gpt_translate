from gpt_translate.loader import remove_markdown_comments, split_markdown, Header, extract_header


def test_remove_markdown_comments():
    # Example usage with your Markdown content
    markdown_content = """
Some content
<!-- This is a comment
It spans multiple lines -->
More content
"""
    cleaned_content = remove_markdown_comments(markdown_content)

    assert cleaned_content == """
Some content

More content
"""

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
    assert chunks[2] == """## Header 1.1
Content under header 1.1"""

def test_header():
    header_ref = """
---
description: Generated documentation for Weights & Biases APIs
---
"""

    header_guide = """
---
slug: /guides/app/features/custom-charts
displayed_sidebar: default
---
"""

    header_multi="""
---
slug: /guides/app/features/panels/weave
description: >-
    Some features on this page are in beta, hidden behind a feature flag. Add
    `weave-plot` to your bio on your profile page to unlock all related features.
displayed_sidebar: default
---
"""

    header, _ = extract_header("")
    header = Header.from_string(header)
    assert str(header) == ""

    header, _ = extract_header(header_ref)
    header = Header.from_string(header)
    assert header.description == "Generated documentation for Weights & Biases APIs"
    assert header.displayed_sidebar == ""
    assert header.slug == ""

    header, _ = extract_header(header_guide)
    header = Header.from_string(header)
    assert header.slug == "/guides/app/features/custom-charts"
    assert header.displayed_sidebar == "default"

    header, _ = extract_header(header_multi)
    header = Header.from_string(header)
    assert header.slug == "/guides/app/features/panels/weave"
    assert header.displayed_sidebar == "default"
    assert header.description == "Some features on this page are in beta, hidden behind a feature flag. Add `weave-plot` to your bio on your profile page to unlock all related features."