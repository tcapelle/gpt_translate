from dataclasses import dataclass
from gpt_translate.evaluate import validate_tabs

@dataclass
class MDPage:
    content: str


def test_validate_tabs_valid():
    content = """
    <Tabs>
        <TabItem value="python" label="Python">
            Python content
        </TabItem>
        <TabItem value="javascript" label="JavaScript">
            JavaScript content
        </TabItem>
    </Tabs>
    """
    page = MDPage(content)
    assert validate_tabs(page, model_output=None)["tabs_format_valid"] is True


def test_validate_tabs_invalid():
    content = """
    <Tabs>
        <TabItem value="python" label="Python">
            Python content
        </TabItem>
        <TabItem value="javascript" label="JavaScript">
            JavaScript content
    </Tabs>
    """
    page = MDPage(content)
    assert validate_tabs(page, model_output=None)["tabs_format_valid"] is False


def test_validate_tabs_format_with_random_text():
    content = """
    Some random text before the tabs.
    <Tabs>
        <TabItem value="python" label="Python">
            Python content
        </TabItem>
        <TabItem value="javascript" label="JavaScript">
            JavaScript content
        </TabItem>
    </Tabs>
    Some random text after the tabs.
    """
    page = MDPage(content)
    assert validate_tabs(page, model_output=None)["tabs_format_valid"] is True
