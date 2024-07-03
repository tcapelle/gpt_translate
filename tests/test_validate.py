from gpt_translate.validate import _validate_tabs_format


def test_validate_tabs_format_valid():
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
    assert _validate_tabs_format(content) == True


def test_validate_tabs_format_invalid():
    content = """
    <Tabs>
        <TabItem value="python" label="Python">
            Python content
        </TabItem>
        <TabItem value="javascript" label="JavaScript">
            JavaScript content
    </Tabs>
    """
    assert _validate_tabs_format(content) == False


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
    assert _validate_tabs_format(content) == True
