import os
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from pathlib import Path

from gpt_translate.utils import (
    file_is_empty, 
    get_md_files, 
    remove_after, 
    longer_create, 
    count_tokens,
    to_weave_dataset
)


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


def test_remove_after():
    "Test the remove_after function with different separators"
    text = "This is a sample text.\nIt has multiple lines.\nAnd some sentences."
    
    # Test with only newline separator - it will find the last occurrence
    result = remove_after(text, sep=["\n"])
    assert result["text"] == "This is a sample text.\nIt has multiple lines.\n"
    assert result["sep_break"] == "\n"
    
    # Test with only period+space separator
    # The function finds the last occurrence which is in "multiple lines."
    text2 = "This is a sample text. It has multiple lines."
    result = remove_after(text2, sep=[". "])
    assert result["text"] == "This is a sample text. "
    assert result["sep_break"] == ". "
    
    # Test with custom separators list
    result = remove_after(text, sep=["lines.", "sample", "not_found"])
    # It should find "lines." since it's in the list and exists in the text
    assert result["text"] == "This is a sample text.\nIt has multiple lines."
    assert result["sep_break"] == "lines."
    
    # Test with no matching separator
    text_without_seps = "ThisTextHasNoSeparators"
    result = remove_after(text_without_seps)
    assert result["text"] == text_without_seps
    assert result["sep_break"] is None


def test_count_tokens():
    "Test token counting function"
    # Simple test with known token counts
    short_text = "Hello world"
    assert count_tokens(short_text) > 0  # Should have at least one token
    
    longer_text = "This is a longer text that should have more tokens than the short one."
    assert count_tokens(longer_text) > count_tokens(short_text)
    
    # Unicode text
    unicode_text = "こんにちは世界"  # "Hello world" in Japanese
    assert count_tokens(unicode_text) > 0


@pytest.mark.asyncio
@patch('gpt_translate.utils.acompletion')
async def test_longer_create_without_recursion(mock_acompletion):
    "Test longer_create when no recursion is needed"
    # Mock a completion that doesn't need recursion
    mock_completion = AsyncMock()
    mock_completion.choices = [
        type('Choice', (), {'message': type('Message', (), {'content': 'Test response'}), 
                          'finish_reason': 'stop'})
    ]
    mock_completion.usage = {"total_tokens": 10}
    mock_acompletion.return_value = mock_completion
    
    messages = [{"role": "user", "content": "Test prompt"}]
    result = await longer_create(messages=messages, max_tokens=100, model="test-model")
    
    mock_acompletion.assert_called_once()
    assert result == "Test response"


@pytest.mark.asyncio
@patch('gpt_translate.utils.acompletion')
@patch('gpt_translate.utils.remove_after')
async def test_longer_create_with_recursion(mock_remove_after, mock_acompletion):
    "Test longer_create with recursion when max tokens are reached"
    # First call hits max tokens
    first_completion = AsyncMock()
    first_completion.choices = [
        type('Choice', (), {'message': type('Message', (), {'content': 'First part of response'}), 
                          'finish_reason': 'length'})
    ]
    first_completion.usage = {"total_tokens": 50}
    
    # Second call completes successfully
    second_completion = AsyncMock()
    second_completion.choices = [
        type('Choice', (), {'message': type('Message', (), {'content': 'Second part of response'}), 
                          'finish_reason': 'stop'})
    ]
    second_completion.usage = {"total_tokens": 50}
    
    mock_acompletion.side_effect = [first_completion, second_completion]
    
    # Mock remove_after to return a processed first part
    mock_remove_after.return_value = {"text": "Processed first part", "sep_break": "\n"}
    
    messages = [{"role": "user", "content": "Test prompt"}]
    result = await longer_create(messages=messages, max_tokens=100, model="test-model")
    
    # Check that acompletion was called twice
    assert mock_acompletion.call_count == 2
    
    # Check that remove_after was called once
    mock_remove_after.assert_called_once_with("First part of response")
    
    # Check that the result is the concatenation of both parts
    assert result == "Processed first partSecond part of response"


@patch('weave.Dataset')
def test_to_weave_dataset(mock_dataset_class):
    "Test creating a weave dataset from translation results"
    # Mock the Dataset class
    mock_dataset = MagicMock()
    mock_dataset_class.return_value = mock_dataset
    
    # Create test data - these would normally be MDPage objects
    class MockMDPage:
        def __init__(self, content):
            self.content = content
    
    # Create mock translation results
    rows = [
        {
            "input_file": "file1.md",
            "output_file": "file1_ja.md",
            "language": "ja",
            "original_page": MockMDPage("Original content 1"),
            "translated_page": MockMDPage("Translated content 1")
        },
        {
            "input_file": "file2.md",
            "output_file": "file2_ja.md",
            "language": "ja",
            "original_page": MockMDPage("Original content 2"),
            "translated_page": MockMDPage("Translated content 2")
        }
    ]
    
    # Call the function
    result = to_weave_dataset("test-dataset", rows)
    
    # Verify the dataset was created correctly
    mock_dataset_class.assert_called_once_with(
        name="test-dataset", 
        description="Translation files", 
        rows=[
            {
                "input_file": "file1.md",
                "output_file": "file1_ja.md",
                "language": "ja",
                "original_doc": "Original content 1",
                "translated_doc": "Translated content 1"
            },
            {
                "input_file": "file2.md",
                "output_file": "file2_ja.md",
                "language": "ja",
                "original_doc": "Original content 2",
                "translated_doc": "Translated content 2"
            }
        ]
    )
    assert result == mock_dataset


@patch('weave.Dataset')
def test_to_weave_dataset_empty_input(mock_dataset_class):
    "Test handling empty input to weave dataset function"
    # Create empty rows
    rows = []
    
    # Mock Dataset to raise an exception with empty rows
    mock_dataset_class.side_effect = Exception("Empty rows are not allowed")
    
    # Call the function - this should raise an exception from the mocked Dataset class
    with pytest.raises(Exception):
        to_weave_dataset("test-dataset", rows)
    
    # Verify that Dataset was called with empty rows
    mock_dataset_class.assert_called_once_with(
        name="test-dataset", 
        description="Translation files", 
        rows=[]
    )
