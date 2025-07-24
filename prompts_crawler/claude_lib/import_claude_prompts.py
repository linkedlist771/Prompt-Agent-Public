import json
from pathlib import Path

from loguru import logger

from prompt_agent.vector_db.prompt_vector_db import get_prompt_vector_db


def import_claude_prompts():
    """
    从prompts.json文件导入Claude prompts到向量数据库
    优先使用system_prompt，如果不存在则使用user_prompt
    """
    # 读取JSON文件
    json_file_path = Path("prompts.json")

    if not json_file_path.exists():
        logger.error(f"JSON文件不存在: {json_file_path}")
        return

    with open(json_file_path, "r", encoding="utf-8") as f:
        prompts_data = json.load(f)

    # 获取向量数据库实例
    vector_db = get_prompt_vector_db()

    # 准备批量插入的数据
    documents = []
    metadatas = []
    ids = []

    for i, prompt in enumerate(prompts_data):
        # 优先使用system_prompt，如果不存在则使用user_prompt
        prompt_content = prompt.get("system_prompt")
        if not prompt_content:
            prompt_content = prompt.get("user_prompt", "")

        if not prompt_content:
            logger.warning(f"跳过空prompt: {prompt.get('title', 'Unknown')}")
            continue

        # 添加到批量数据
        documents.append(prompt_content)
        metadatas.append(
            {
                "title": prompt.get("title", ""),
                "url": prompt.get("url", ""),
                "source": "claude_lib",
                "has_system_prompt": bool(prompt.get("system_prompt")),
                "has_user_prompt": bool(prompt.get("user_prompt")),
            }
        )
        ids.append(f"claude_prompt_{i}")

    # 批量添加到向量数据库
    try:
        result = vector_db.add(documents=documents, metadatas=metadatas, ids=ids)
        logger.info(f"成功导入 {len(documents)} 条Claude prompts到向量数据库")
        logger.info(f"导入结果: {result}")

        # 显示导入后的统计信息
        total_count = vector_db.count()
        logger.info(f"向量数据库总文档数: {total_count}")

    except Exception as e:
        logger.error(f"导入向量数据库时出错: {e}")


if __name__ == "__main__":
    import_claude_prompts()
