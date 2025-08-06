import os
import asyncio
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from pathlib import Path

from gpt_translate.utils import (
    file_is_empty, 
    get_md_files, 
    remove_after, 
    longer_create, 
    count_tokens,
    to_weave_dataset,
    gather_with_progress,
    logger
)
from rich.progress import Progress
from rich.console import Console
import logging


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


# Tests for gather_with_progress function
async def mock_task(delay: float, task_id: int, should_fail: bool = False):
    """Mock async task that simulates some work"""
    await asyncio.sleep(delay)
    if should_fail:
        raise Exception(f"Mock error in task {task_id}")
    return {"task_id": task_id, "result": f"completed task {task_id}", "error": None}


@pytest.mark.asyncio
async def test_gather_with_progress_empty_tasks():
    """Test gather_with_progress with empty task list"""
    tasks = []
    results = await gather_with_progress(tasks, "Testing empty list")
    assert results == []


@pytest.mark.asyncio
async def test_gather_with_progress_single_task():
    """Test gather_with_progress with a single task"""
    tasks = [mock_task(0.1, 1)]
    results = await gather_with_progress(tasks, "Testing single task")
    
    assert len(results) == 1
    assert results[0]["task_id"] == 1
    assert results[0]["result"] == "completed task 1"
    assert results[0]["error"] is None


@pytest.mark.asyncio
async def test_gather_with_progress_multiple_tasks():
    """Test gather_with_progress with multiple successful tasks"""
    tasks = [
        mock_task(0.1, 1),
        mock_task(0.05, 2),
        mock_task(0.15, 3),
        mock_task(0.02, 4),
    ]
    
    results = await gather_with_progress(tasks, "Testing multiple tasks")
    
    assert len(results) == 4
    # Check that results are in the correct order (same as input tasks)
    for i, result in enumerate(results):
        assert result["task_id"] == i + 1
        assert result["result"] == f"completed task {i + 1}"
        assert result["error"] is None


@pytest.mark.asyncio
async def test_gather_with_progress_with_failures():
    """Test gather_with_progress with some failing tasks"""
    tasks = [
        mock_task(0.1, 1),
        mock_task(0.05, 2, should_fail=True),  # This one fails
        mock_task(0.15, 3),
        mock_task(0.02, 4, should_fail=True),  # This one also fails
    ]
    
    results = await gather_with_progress(tasks, "Testing with failures")
    
    assert len(results) == 4
    
    # Check successful tasks
    assert results[0]["task_id"] == 1
    assert results[0]["error"] is None
    assert results[2]["task_id"] == 3
    assert results[2]["error"] is None
    
    # Check failed tasks
    assert results[1]["error"] == "Mock error in task 2"
    assert results[3]["error"] == "Mock error in task 4"


@pytest.mark.asyncio
async def test_gather_with_progress_preserves_order():
    """Test that gather_with_progress preserves task order even when tasks complete out of order"""
    # Create tasks where the first one takes longest, last one completes first
    tasks = [
        mock_task(0.2, 1),   # Slowest
        mock_task(0.1, 2),   # Medium
        mock_task(0.05, 3),  # Fast
        mock_task(0.01, 4),  # Fastest
    ]
    
    results = await gather_with_progress(tasks, "Testing order preservation")
    
    assert len(results) == 4
    # Even though task 4 completes first, it should be in position 3 (index 3)
    # and task 1 should be in position 0 (index 0) even though it completes last
    assert results[0]["task_id"] == 1
    assert results[1]["task_id"] == 2
    assert results[2]["task_id"] == 3
    assert results[3]["task_id"] == 4


@pytest.mark.asyncio
async def test_gather_with_progress_all_failures():
    """Test gather_with_progress when all tasks fail"""
    tasks = [
        mock_task(0.1, 1, should_fail=True),
        mock_task(0.05, 2, should_fail=True),
        mock_task(0.02, 3, should_fail=True),
    ]
    
    results = await gather_with_progress(tasks, "Testing all failures")
    
    assert len(results) == 3
    for i, result in enumerate(results):
        assert result["error"] == f"Mock error in task {i + 1}"


@pytest.mark.asyncio
async def test_gather_with_progress_custom_description():
    """Test that gather_with_progress uses custom description"""
    async def simple_task():
        await asyncio.sleep(0.01)
        return "done"
    
    tasks = [simple_task()]
    
    # Test with custom description - this is more of an integration test
    # to ensure the function works with different descriptions
    results = await gather_with_progress(tasks, "Custom test description")
    
    assert len(results) == 1
    assert results[0] == "done"


@pytest.mark.asyncio 
async def test_gather_with_progress_mixed_result_types():
    """Test gather_with_progress with tasks returning different result types"""
    async def string_task():
        await asyncio.sleep(0.01)
        return "string result"
        
    async def dict_task():
        await asyncio.sleep(0.01)
        return {"type": "dict", "value": 42}
        
    async def list_task():
        await asyncio.sleep(0.01)
        return [1, 2, 3]
    
    tasks = [string_task(), dict_task(), list_task()]
    results = await gather_with_progress(tasks, "Testing mixed types")
    
    assert len(results) == 3
    assert results[0] == "string result"
    assert results[1] == {"type": "dict", "value": 42}
    assert results[2] == [1, 2, 3]


@pytest.mark.asyncio
async def test_gather_with_progress_custom_progress_object():
    """Test gather_with_progress with a custom Progress object"""
    async def simple_task():
        await asyncio.sleep(0.01)
        return "custom progress test"
    
    tasks = [simple_task(), simple_task()]
    
    # Create a custom progress object
    console = Console()
    with Progress(console=console, transient=True) as custom_progress:
        results = await gather_with_progress(
            tasks, 
            "Testing custom progress", 
            progress=custom_progress
        )
    
    assert len(results) == 2
    assert all(result == "custom progress test" for result in results)


def test_rich_logger_configuration():
    """Test that the Rich logger is properly configured"""
    assert logger.name == "gpt_translate"
    
    # Test that importing from different places gives the same logger
    from gpt_translate.utils import logger as utils_logger
    from gpt_translate.translate import logger as translate_logger
    from gpt_translate.loader import logger as loader_logger
    from gpt_translate.evaluate import logger as evaluate_logger
    
    # All should be the same logger instance
    assert utils_logger is translate_logger
    assert translate_logger is loader_logger  
    assert loader_logger is evaluate_logger
    assert logger is utils_logger


def test_logger_functionality():
    """Test that the logger works with Rich formatting"""
    # This is more of a smoke test to ensure no exceptions are raised
    logger.info("Test info message")
    logger.warning("Test warning message") 
    logger.error("Test error message")
    
    # Test exception logging
    try:
        1 / 0
    except Exception:
        logger.exception("Test exception logging")
    
    # If we get here without exceptions, the logger is working
