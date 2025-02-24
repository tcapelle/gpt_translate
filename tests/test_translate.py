import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from pathlib import Path

from gpt_translate.translate import translate_content, TranslationResult
from gpt_translate.loader import MDPage, Header


@pytest.mark.asyncio
@patch('gpt_translate.translate.longer_create')
async def test_translate_content(mock_longer_create):
    """Test the translate_content function with a mocked longer_create"""
    # Setup mock
    mock_longer_create.return_value = "Translated content"
    prompt_mock = MagicMock()
    prompt_mock.format.return_value = [{"role": "user", "content": "Translate this"}]
    
    # Call the function
    result = await translate_content("Test markdown", prompt_mock, model="test-model")
    
    # Verify mock calls
    mock_longer_create.assert_called_once()
    prompt_mock.format.assert_called_once_with(md_chunk="Test markdown")
    
    # Check return value
    assert isinstance(result, TranslationResult)
    assert result.content == "Translated content"
    assert result.tokens > 0


@pytest.mark.asyncio
async def test_semaphore_concurrency():
    """Test that semaphore properly limits concurrency"""
    # Variables to track concurrency
    max_concurrent = 0
    current_concurrent = 0
    
    # Create a semaphore with limit of 2
    semaphore = asyncio.Semaphore(2)
    
    # Test function that uses the semaphore
    async def task_with_semaphore(i):
        nonlocal current_concurrent, max_concurrent
        
        async with semaphore:
            # Track concurrency
            current_concurrent += 1
            max_concurrent = max(max_concurrent, current_concurrent)
            
            # Simulate work with variable duration
            await asyncio.sleep(0.01 * (i % 3 + 1))
            
            current_concurrent -= 1
            return i
    
    # Create 5 tasks - if they all ran at once, max_concurrent would be 5
    tasks = [task_with_semaphore(i) for i in range(5)]
    
    # Run all tasks
    results = await asyncio.gather(*tasks)
    
    # The semaphore should have limited concurrency to 2
    assert max_concurrent == 2
    
    # All tasks should have completed
    assert len(results) == 5
    assert sorted(results) == [0, 1, 2, 3, 4]