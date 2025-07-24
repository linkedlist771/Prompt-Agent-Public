import asyncio
from functools import lru_cache, partial
from http.client import responses
from typing import AsyncGenerator, Dict, List, Union

from loguru import logger

from prompt_agent.configs import (DEFAULT_MODEL, DEFAULT_RETRIVAL_COUNT,
                                  ENABLE_VECTOR_DB_RETRIVAL,
                                  OUTPUT_PROMPT_END_TAG,
                                  OUTPUT_PROMPT_START_TAG)
from prompt_agent.prompts import OPTIMIZE_PROMPT, RAG_REFER_PROMPT
from prompt_agent.provider import async_client
from prompt_agent.vector_db.prompt_vector_db import get_prompt_vector_db

# 不写设计模式了， 什么继承之类的

prompt_vector_db = get_prompt_vector_db()


class PromptAgent(object):
    def __init__(self):
        self.client = async_client

    async def filter_prompt_generator(
        self, raw_llm_stream: AsyncGenerator
    ) -> AsyncGenerator:
        # TODO: still has bug, I need to check and fix this yet.
        accumulated_text = ""
        hit_start_tag = False
        hit_end_tag = False
        yielded_length = 0
        potential_end_tag_buffer = ""  # 缓存可能的结束标签部分

        async for chunk in raw_llm_stream:
            text = chunk.choices[0].delta.content
            text = text or ""

            if not hit_start_tag:
                # 还未找到开始标签，继续累积
                accumulated_text += text
                if OUTPUT_PROMPT_START_TAG in accumulated_text:
                    # 首次命中开始标签
                    start_pos = accumulated_text.find(OUTPUT_PROMPT_START_TAG)
                    content_start = start_pos + len(OUTPUT_PROMPT_START_TAG)
                    remaining = accumulated_text[content_start:]
                    if remaining:
                        yield remaining
                    yielded_length = len(accumulated_text)
                    hit_start_tag = True

            elif hit_start_tag and not hit_end_tag:
                # 已找到开始标签，正在查找结束标签
                # 将新文本添加到缓冲区
                potential_end_tag_buffer += text

                # 检查缓冲区中是否包含完整的结束标签
                if OUTPUT_PROMPT_END_TAG in potential_end_tag_buffer:
                    # 找到完整的结束标签
                    end_pos = potential_end_tag_buffer.find(OUTPUT_PROMPT_END_TAG)
                    # 输出结束标签之前的内容
                    content_before_end = potential_end_tag_buffer[:end_pos]
                    if content_before_end:
                        yield content_before_end
                    hit_end_tag = True
                    return
                # 检查缓冲区是否可能包含结束标签的前缀
                # 找出最长的可能前缀
                max_prefix_len = 0
                for i in range(
                    1,
                    min(len(potential_end_tag_buffer) + 1, len(OUTPUT_PROMPT_END_TAG)),
                ):
                    if potential_end_tag_buffer.endswith(OUTPUT_PROMPT_END_TAG[:i]):
                        max_prefix_len = i

                if max_prefix_len > 0:
                    # 缓冲区末尾可能是结束标签的开始
                    # 保留可能的前缀，输出其他内容
                    safe_to_yield = potential_end_tag_buffer[:-max_prefix_len]
                    if safe_to_yield:
                        yield safe_to_yield
                        accumulated_text += safe_to_yield
                        yielded_length = len(accumulated_text)
                    # 保留可能的前缀在缓冲区中
                    potential_end_tag_buffer = potential_end_tag_buffer[
                        -max_prefix_len:
                    ]
                else:
                    # 缓冲区中没有结束标签的前缀，可以安全输出所有内容
                    if potential_end_tag_buffer:
                        yield potential_end_tag_buffer
                        accumulated_text += potential_end_tag_buffer
                        yielded_length = len(accumulated_text)
                    potential_end_tag_buffer = ""

    async def optimize_prompt(
        self,
        original_prompt: str | None = None,
        messages: List[Dict[str, str]] | None = None,
        stream: bool = True,
        enable_vector_db_retrival: bool = False,
        collection_name: str = "",
    ) -> AsyncGenerator | str:
        if messages:
            # Use the provided messages directly
            _messages = [
                {"role": msg["role"], "content": msg["content"]} for msg in messages
            ]

            original_prompt = _messages[-1]["content"]
            if enable_vector_db_retrival:
                # TODO: 这个rag可以后面再优化。
                query_partial = partial(
                    prompt_vector_db.query,
                    query_texts=[original_prompt],
                    n_results=DEFAULT_RETRIVAL_COUNT,
                    collection_name=collection_name,
                )
                retrieved_prompt_templates = await asyncio.to_thread(query_partial)
                logger.debug(
                    f"retrieved_prompt_templates:\n{retrieved_prompt_templates}"
                )
                _prompt_templates = retrieved_prompt_templates["documents"][0]  # list
                _prompt_templates_str = ""
                for idx, prompt_template in enumerate(_prompt_templates):
                    idx += 1
                    _prompt_templates_str += f"{idx}. {prompt_template}\n"
                prompt_templates = RAG_REFER_PROMPT + _prompt_templates_str
            else:
                prompt_templates = ""

            logger.debug(f"RAG IS :\n{enable_vector_db_retrival}")

            last_content = OPTIMIZE_PROMPT.format(
                prompt=original_prompt, prompt_templates=prompt_templates
            )
            logger.debug(f"final prompt:\n{last_content}")
            _messages[-1] = {
                "role": _messages[-1]["role"],
                "content": last_content,
            }
        else:
            raise NotImplementedError
            # # Fallback to original_prompt if no messages provided
            # assert original_prompt, "original_prompt should exist when messages is None"
            # message_prompt = OPTIMIZE_PROMPT.format(prompt=original_prompt)
            # _messages = [
            #     {
            #         "role": "system",
            #         "content": message_prompt,
            #     }
            # ]

        # Ensure DEFAULT_MODEL is not None
        model = DEFAULT_MODEL

        _stream = await self.client.chat.completions.create(
            model=model, messages=_messages, stream=stream
        )

        if stream:
            response_text = ""
            async for chunk in self.filter_prompt_generator(_stream):
                yield chunk
                response_text += chunk

            logger.debug(f"response_text:\n{response_text}")
        else:
            raise NotImplementedError
            # Handle non-streaming response
            # return _stream.choices[0].message.content or ""


@lru_cache
def get_prompt_agent():
    return PromptAgent()


async def main():
    prompt_agent = PromptAgent()
    original_prompt = """from typing import List




class Solution:
    def subarraySum(self, nums: List[int], k: int) -> int:
        prefix_sub = [0]
        sumation = 0
        count = 0
        for num in nums:
            sumation += num
            if sumation - k in  prefix_sub: # 减掉这个一定在前缀和里面。
                count += 1
            prefix_sub.append(sumation)
        # if sumation - k in prefix_sub:  # 减掉这个一定在前缀和里面。
        #     count += 1




        return count











为什么过不了"""
    #     original_prompt = "你好？ 你是什么模型？"
    messages = [
        {
            "role": "user",
            "content": original_prompt,
        }
    ]
    # async for text in prompt_agent.optimize_prompt(messages=messages, stream=True):
    #     print(text, end="")
    # if text.choices[0].delta.content:
    #     print(text.choices[0].delta.content, end="")


if __name__ == "__main__":
    asyncio.run(main())
