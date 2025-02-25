import os
import pytest
from pathlib import Path
import tempfile
import asyncio

from gpt_translate.translate import (
    Translator,
    translate_content,
    _translate_file,
)
from gpt_translate.loader import MDPage, Header
from gpt_translate.prompts import PromptTemplate
from gpt_translate.utils import longer_create

if "GOOGLE_API_KEY" in os.environ:
    MODEL_NAME = "gemini/gemini-2.0-flash"
elif "OPENAI_API_KEY" in os.environ:
    MODEL_NAME = "gpt-4o-mini"
else:
    raise ValueError("No API key found in environment variables")

# Skip these tests if no API key is available
requires_api_key = pytest.mark.skipif(
    "GOOGLE_API_KEY" not in os.environ and "OPENAI_API_KEY" not in os.environ,
    reason="Requires GOOGLE_API_KEY or OPENAI_API_KEY environment variable"
)


@requires_api_key
@pytest.mark.asyncio
async def test_translate_content_live():
    """Test translate_content with real API call"""
    # Create a simple prompt template for testing
    test_file_path = Path("tests/data/intro.md")
    test_content = test_file_path.read_text()
    
    # Load configs from the project
    config_folder = Path("./configs")
    prompt_template = PromptTemplate.from_folder(config_folder, language="es")
    
    # Use OpenAI model
    model_args = {
        "model": MODEL_NAME,
        "temperature": 0.7,
        "max_tokens": 1000
    }
    
    # Test with a small chunk of markdown
    small_chunk = "# Hello World\n\nThis is a test paragraph."
    result = await translate_content(small_chunk, prompt_template, **model_args)
    
    # Verify that we got a valid translation
    assert result.content
    assert len(result.content) > 10
    assert result.tokens > 0
    print(f"Translated content: {result.content}")


@requires_api_key
@pytest.mark.asyncio
async def test_translator_live():
    """Test the Translator class with a real API call"""
    # Create a test translator
    translator = Translator(
        config_folder="./configs",
        language="es",
        model_args={
            "model": MODEL_NAME,
            "temperature": 0.7
        }
    )
    
    # Create a simple test page
    header = Header(
        title="Test Title", 
        description="This is a test description for translation."
    )
    test_page = MDPage(
        filename="test.md",
        content="# Test Content\n\nThis is a paragraph for testing translation.",
        header=header
    )
    
    # Translate the page
    translated_page = await translator.translate_page(test_page)
    
    # Verify the translation
    assert translated_page.content
    assert len(translated_page.content) > 10
    print(f"Translated page content: {translated_page.content}")
    
    # If header translation is enabled, check that too
    if translator.do_translate_header_description:
        assert translated_page.header.description
        assert translated_page.header.description != test_page.header.description
        print(f"Translated header: {translated_page.header.description}")


@requires_api_key
@pytest.mark.asyncio
async def test_translate_file_live():
    """Test the file translation with a real API call"""
    # Create a temporary test file
    with tempfile.NamedTemporaryFile(suffix=".md", mode="w+", encoding="utf-8", delete=False) as temp_file:
        temp_file.write("# Test File\n\nThis is a test file for translation.")
        temp_path = temp_file.name
    
    try:
        # Create a temporary output file
        output_path = f"{temp_path}_es.md"
        
        # Translate the file
        result = await _translate_file(
            input_file=temp_path,
            out_file=output_path,
            language="es",
            config_folder="./configs",
            model_args={
                "model": MODEL_NAME,
                "temperature": 0.7
            }
        )
        
        # Verify the result
        assert result["error"] is None
        assert Path(output_path).exists()
        
        # Read the translated content
        translated_content = Path(output_path).read_text()
        print(f"Translated file content: {translated_content}")
        
        assert len(translated_content) > 10
    finally:
        # Clean up temporary files
        for path in [temp_path, output_path]:
            if Path(path).exists():
                Path(path).unlink()


@requires_api_key
@pytest.mark.asyncio
async def test_batch_translate_live():
    """Test concurrent translation of multiple files"""
    from gpt_translate.translate import _translate_file
    import asyncio
    
    # Create multiple temporary test files
    temp_files = []
    for i in range(2):  # Use a small number for faster tests
        with tempfile.NamedTemporaryFile(suffix=".md", mode="w+", encoding="utf-8", delete=False) as temp_file:
            temp_file.write(f"# Test File {i}\n\nThis is test file {i} for batch translation.")
            temp_files.append(Path(temp_file.name))
    
    # Create a temporary output directory
    with tempfile.TemporaryDirectory() as temp_output_dir:
        output_dir = Path(temp_output_dir)
        
        try:
            # Test with semaphore to manage concurrency
            semaphore = asyncio.Semaphore(1)  # Limit to 1 concurrent request
            
            async def translate_with_semaphore(file_path):
                async with semaphore:
                    out_file = output_dir / file_path.name
                    return await _translate_file(
                        input_file=str(file_path),
                        out_file=str(out_file),
                        language="es",
                        config_folder="./configs",
                        model_args={
                            "model": MODEL_NAME,
                            "temperature": 0.7
                        }
                    )
            
            # Run concurrent translations
            tasks = [translate_with_semaphore(file) for file in temp_files]
            results = await asyncio.gather(*tasks)
            
            # Verify the results
            successful_translations = [r for r in results if r["error"] is None]
            assert len(successful_translations) > 0
            
            # Verify the outputs
            output_files = list(output_dir.glob("*.md"))
            assert len(output_files) > 0
            
            # Check content of output files
            for output_file in output_files:
                content = output_file.read_text()
                assert len(content) > 0
                print(f"Batch translated file {output_file.name}: {content[:50]}...")
                
        finally:
            # Clean up temporary input files
            for file_path in temp_files:
                if file_path.exists():
                    file_path.unlink()


@requires_api_key
@pytest.mark.asyncio
async def test_longer_create_live():
    """Test the longer_create function with a real model call that might need recursion"""
    # Create a message that should yield a long response
    prompt = "Please generate a detailed tutorial on markdown syntax with examples for each feature. Include sections on headers, lists, code blocks, tables, links, images, and formatting. Each section should have complete examples."
    
    messages = [
        {"role": "system", "content": "You are a helpful technical assistant."},
        {"role": "user", "content": prompt}
    ]
    
    # Use a model that's likely to produce long outputs
    model_args = {
        "model": MODEL_NAME,  # Could use a larger model if available
        "temperature": 0.7,
        # Use a small max_tokens to force recursion
        "max_tokens": 1000  
    }
    
    # Call longer_create
    result = await longer_create(messages=messages, **model_args)
    
    # Verify that we got a full, complete response
    assert result
    assert len(result) > 500  # Should be a substantial response
    
    # Check for common markdown elements that should be in the response
    markdown_elements = ["#", "```", "**", "- ", "| ", "[", "!["]
    present_elements = [elem for elem in markdown_elements if elem in result]
    assert len(present_elements) >= 4, "Response should contain multiple markdown elements"
    
    print(f"Longer create result length: {len(result)} chars")
    print(f"Result excerpt: {result[:200]}...")


if __name__ == "__main__":
    # Run the tests directly if needed
    asyncio.run(test_translate_content_live())