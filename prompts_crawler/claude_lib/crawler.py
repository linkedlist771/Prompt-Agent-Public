import asyncio
import re
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger
from pydantic import BaseModel


class Prompt(BaseModel):
    title: str
    system_prompt: Optional[str] = None
    user_prompt: Optional[str] = None
    url: str


hrefs = [
    "/en/prompt-library/cosmic-keystrokes",
    "/en/prompt-library/corporate-clairvoyant",
    "/en/prompt-library/website-wizard",
    "/en/prompt-library/excel-formula-expert",
    "/en/prompt-library/google-apps-scripter",
    "/en/prompt-library/python-bug-buster",
    "/en/prompt-library/time-travel-consultant",
    "/en/prompt-library/storytelling-sidekick",
    "/en/prompt-library/cite-your-sources",
    "/en/prompt-library/sql-sorcerer",
    "/en/prompt-library/dream-interpreter",
    "/en/prompt-library/pun-dit",
    "/en/prompt-library/culinary-creator",
    "/en/prompt-library/portmanteau-poet",
    "/en/prompt-library/hal-the-humorous-helper",
    "/en/prompt-library/latex-legend",
    "/en/prompt-library/mood-colorizer",
    "/en/prompt-library/git-gud",
    "/en/prompt-library/simile-savant",
    "/en/prompt-library/ethical-dilemma-navigator",
    "/en/prompt-library/meeting-scribe",
    "/en/prompt-library/idiom-illuminator",
    "/en/prompt-library/code-consultant",
    "/en/prompt-library/function-fabricator",
    "/en/prompt-library/neologism-creator",
    "/en/prompt-library/csv-converter",
    "/en/prompt-library/emoji-encoder",
    "/en/prompt-library/prose-polisher",
    "/en/prompt-library/perspectives-ponderer",
    "/en/prompt-library/trivia-generator",
    "/en/prompt-library/mindfulness-mentor",
    "/en/prompt-library/second-grade-simplifier",
    "/en/prompt-library/vr-fitness-innovator",
    "/en/prompt-library/pii-purifier",
    "/en/prompt-library/memo-maestro",
    "/en/prompt-library/career-coach",
    "/en/prompt-library/grading-guru",
    "/en/prompt-library/tongue-twister",
    "/en/prompt-library/interview-question-crafter",
    "/en/prompt-library/grammar-genie",
    "/en/prompt-library/riddle-me-this",
    "/en/prompt-library/code-clarifier",
    "/en/prompt-library/alien-anthropologist",
    "/en/prompt-library/data-organizer",
    "/en/prompt-library/brand-builder",
    "/en/prompt-library/efficiency-estimator",
    "/en/prompt-library/review-classifier",
    "/en/prompt-library/direction-decoder",
    "/en/prompt-library/motivational-muse",
    "/en/prompt-library/email-extractor",
    "/en/prompt-library/master-moderator",
    "/en/prompt-library/lesson-planner",
    "/en/prompt-library/socratic-sage",
    "/en/prompt-library/alliteration-alchemist",
    "/en/prompt-library/futuristic-fashion-advisor",
    "/en/prompt-library/polyglot-superpowers",
    "/en/prompt-library/product-naming-pro",
    "/en/prompt-library/philosophical-musings",
    "/en/prompt-library/spreadsheet-sorcerer",
    "/en/prompt-library/sci-fi-scenario-simulator",
    "/en/prompt-library/adaptive-editor",
    "/en/prompt-library/babels-broadcasts",
    "/en/prompt-library/tweet-tone-detector",
    "/en/prompt-library/airport-code-analyst",
]

CLAUDE_PROMPTS_URL_PREFIX = "https://docs.anthropic.com"


def parse_markdown_content(content: str, url: str) -> Optional[Prompt]:
    """
    解析markdown内容，提取title、system prompt和user prompt
    如果有多个System或User行，只提取第一个
    """
    try:
        # 提取标题 (# 开头的第一行)
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else "Unknown Title"

        system_prompt = None
        user_prompt = None

        # 查找表格中的所有System和User行
        # 匹配表格行格式: | System | 内容 | 或 | User | 内容 |
        table_rows = re.findall(
            r"\|\s*(System|User)\s*\|\s*(.+?)\s*\|", content, re.DOTALL | re.IGNORECASE
        )

        if table_rows:
            # 提取第一个System和第一个User
            for row_type, row_content in table_rows:
                if row_type.lower() == "system" and system_prompt is None:
                    system_prompt = row_content.strip()
                elif row_type.lower() == "user" and user_prompt is None:
                    user_prompt = row_content.strip()

                # 如果已经找到了第一个System和第一个User，就停止
                if system_prompt is not None and user_prompt is not None:
                    break
        else:
            # 如果没有找到表格格式，尝试其他格式
            # 查找 System: 和 User: 标记（只取第一个）
            system_match = re.search(
                r"System[:\s]*(.+?)(?=User[:\s]|System[:\s]|$)",
                content,
                re.DOTALL | re.IGNORECASE,
            )
            user_match = re.search(
                r"User[:\s]*(.+?)(?=System[:\s]|User[:\s]|$)",
                content,
                re.DOTALL | re.IGNORECASE,
            )

            if system_match:
                system_prompt = system_match.group(1).strip()
            if user_match:
                user_prompt = user_match.group(1).strip()

        # 清理prompt内容，移除markdown格式
        if system_prompt:
            system_prompt = clean_prompt_content(system_prompt)
        if user_prompt:
            user_prompt = clean_prompt_content(user_prompt)

        return Prompt(
            title=title, system_prompt=system_prompt, user_prompt=user_prompt, url=url
        )

    except Exception as e:
        logger.error(f"Error parsing content from {url}: {e}")
        return None


def clean_prompt_content(content: str) -> str:
    """
    清理prompt内容，移除多余的markdown格式和空白
    """
    # 移除表格分隔符
    content = re.sub(r"\|\s*-+\s*\|", "", content)
    # 移除多余的竖线
    content = re.sub(r"^\||\|$", "", content, flags=re.MULTILINE)
    # 移除多余的空白行
    content = re.sub(r"\n\s*\n", "\n\n", content)
    # 移除开头和结尾的空白
    content = content.strip()

    return content


async def fetch_prompt_from_url(url: str) -> Optional[str]:
    """
    从URL获取内容
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text
    except Exception as e:
        logger.error(f"Failed to fetch {url}: {e}")
        return None


async def process_single_prompt(href: str) -> Optional[Prompt]:
    """
    处理单个prompt URL
    """
    url = CLAUDE_PROMPTS_URL_PREFIX + href.replace("en", "en/resources") + ".md"
    logger.info(f"Fetching prompt from {url}")

    content = await fetch_prompt_from_url(url)
    if content:
        prompt = parse_markdown_content(content, url)
        if prompt:
            logger.info(f"Successfully parsed: {prompt.title}")
            return prompt
        else:
            logger.warning(f"Failed to parse content from {url}")

    return None


async def fetch_all_prompts() -> List[Prompt]:
    """
    并发获取所有prompts
    """
    tasks = [process_single_prompt(href) for href in hrefs]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    prompts = []
    for result in results:
        if isinstance(result, Prompt):
            prompts.append(result)
        elif isinstance(result, Exception):
            logger.error(f"Task failed with exception: {result}")

    return prompts


async def save_prompts_to_file(prompts: List[Prompt], filename: str = "prompts.json"):
    """
    将prompts保存到文件
    """
    import json

    prompts_data = [prompt.dict() for prompt in prompts]

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(prompts_data, f, ensure_ascii=False, indent=2)

    logger.info(f"Saved {len(prompts)} prompts to {filename}")


async def main():
    """
    主函数
    """
    logger.info("Starting to fetch and parse prompts...")

    # 获取所有prompts
    prompts = await fetch_all_prompts()

    logger.info(f"Successfully parsed {len(prompts)} prompts")

    # 打印一些示例
    for i, prompt in enumerate(prompts[:3]):  # 只显示前3个作为示例
        logger.info(f"\n--- Prompt {i + 1}: {prompt.title} ---")
        logger.info(f"URL: {prompt.url}")
        if prompt.system_prompt:
            logger.info(f"System: {prompt.system_prompt[:100]}...")
        if prompt.user_prompt:
            logger.info(f"User: {prompt.user_prompt[:100]}...")

    # 保存到文件
    await save_prompts_to_file(prompts)

    return prompts


if __name__ == "__main__":
    prompts = asyncio.run(main())
