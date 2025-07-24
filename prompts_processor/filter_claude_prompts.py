import re
from pathlib import Path

from loguru import logger

CLAUDE_PROMPT_MD = Path("claude_prompts.md")

content = CLAUDE_PROMPT_MD.read_text()


def extract_code_blocks(text):
    """
    Extract all code blocks (content between triple backticks) from markdown text
    Returns a list of code block contents
    """
    # Pattern to match code blocks: ``` ... ```
    # Using re.DOTALL to match across multiple lines
    pattern = r"```(?:[a-zA-Z0-9]*\n)?(.*?)```"

    # Find all matches
    code_blocks = re.findall(pattern, text, re.DOTALL)

    # Strip leading/trailing whitespace from each block
    code_blocks = [block.strip() for block in code_blocks]

    return code_blocks


def extract_code_blocks_with_language(text):
    """
    Extract code blocks along with their language specification
    Returns a list of tuples: (language, content)
    """
    pattern = r"```([a-zA-Z0-9]*)\n?(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)

    result = []
    for language, content in matches:
        result.append(
            {"language": language if language else "text", "content": content.strip()}
        )

    return result


# Your existing code
CLAUDE_PROMPT_MD = Path("claude_prompts.md")

# Check if file exists
if CLAUDE_PROMPT_MD.exists():
    content = CLAUDE_PROMPT_MD.read_text(encoding="utf-8")
    logger.debug(f"File content loaded, length: {len(content)}")

    # Extract just the code content
    code_blocks = extract_code_blocks(content)
    logger.info(f"Found {len(code_blocks)} code blocks")

    # Print results
    for i, block in enumerate(code_blocks, 1):
        logger.info(f"Code Block {i}:")
        logger.info(f"Content: {block}")

else:
    logger.error(f"File {CLAUDE_PROMPT_MD} not found")
