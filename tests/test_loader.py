from gpt_translate.loader import remove_markdown_comments, split_markdown


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