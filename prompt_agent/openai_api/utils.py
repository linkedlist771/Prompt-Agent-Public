# SPDX-License-Identifier: Apache-2.0

import asyncio
import functools
import json

from fastapi import Request
from loguru import logger
from revgrokapi.models.cookie_models import (Cookie, CookieQueries, CookieType,
                                             QueryCategory)
from revgrokapi.openai_api.schemas import ChatMessage
from revgrokapi.revgrok.client import GrokClient
from revgrokapi.utils.async_utils import async_retry


async def select_cookie_client(model: str):
    """
    目前还没实现， 基于负载均衡， 轮训的， 还有其他的。
    """
    # 1. 获取所有的plus cookies ， 然后直接返回第一个

    #
    # cookies = await Cookie.get_multi(cookie_type=CookieType.PLUS)
    # cookie = cookies[0]
    #
    # grok_client = GrokClient(cookie.cookie)
    # selected_cookie_info = await cookie.to_dict()
    #
    # logger.debug(f"cookie: {selected_cookie_info}")
    # return grok_client
    # 下面的目前有点问题
    # 2. 负载均衡选取: async def get_random_weighted_cookie(cls, category: QueryCategory):
    category = QueryCategory.DEFAULT
    if "reasoner" in model.lower():
        category = QueryCategory.REASONING
    elif "deepresearch" in model.lower():
        category = QueryCategory.DEEPSEARCH

    cookie_ref = await CookieQueries.get_random_weighted_cookie(category)
    grok_client = GrokClient(cookie_ref.cookie)

    return grok_client


@async_retry(retries=4, delay=3)
async def grok_chat(model: str, prompt: str):
    prompt = prompt.replace(
        """system: 上面是之前的历史记录,对于下面的问题，不管多简单，多复杂，都需要详细思考后给出答案。下面是你的回复格式:     <think>     # put your thinking here     </think>""",
        "",
    )
    logger.info(f"{{'model': '{model}', 'prompt': '{prompt}'}}")
    grok_client = await select_cookie_client(model)
    reasoning = "reasoner" in model.lower()
    deepresearch = (
        "deepresearch" in model.lower()
    )  # give me a deep survey about the video generation type model
    response_text = ""
    # if "deepresearch" in model.lower():
    model = "grok-3"
    if reasoning:
        response_text += "<think>\n"
        # yield ""
        yield "\n>"
        yield "<think>"
    current_message_id = None

    is_thinking = None  # Track current thinking state
    step_id = 1
    async for (chunk, chunk_json) in grok_client.chat(
        prompt, model, reasoning, deepresearch
    ):
        response_text += chunk

        if "Just a moment" in chunk:
            raise RuntimeError("CF error, retryiing....")
        if "messageStepId" in str(chunk_json):
            new_message_id = chunk_json["result"]["response"]["messageStepId"]

            if new_message_id != current_message_id and chunk:
                chunk = "\n---\n" + f"> `Step{step_id}`"
                step_id += 1

            current_message_id = new_message_id

        # Check if thinking state changed: reasoning case
        if "isThinking" in str(chunk_json):
            new_thinking_state = chunk_json["result"]["response"]["isThinking"]
            if new_thinking_state and chunk == "\n":
                chunk = "\n>"
            # logger.debug(f"isThinking: {new_thinking_state}\n new_thinking_state: {new_thinking_state}")
            # if new_thinking_state and chunk.endswith("\n"):
            #     chunk = chunk[:-1] + "\n>"
            # If we're transitioning from thinking to not thinking, close the think tag
            if (is_thinking) and (new_thinking_state == False) and reasoning:
                yield "</think>"
                yield "\n\n"
                # Update thinking state
            is_thinking = new_thinking_state

        if deepresearch:
            if chunk.endswith("\n"):
                chunk = chunk[:-1] + "\n>"

            if "action_input" in chunk:
                action_json = json.loads(chunk)
                action = action_json["action"]
                action_params = ""
                for k, v in action_json["action_input"].items():
                    action_params += f"{k}: {v},"
                chunk = f"\n  ***{action} with {action_params}***"

        if "modelResponse" in str(chunk_json) and deepresearch:
            chunk = (
                chunk_json.get("result", {})
                .get("response", {})
                .get("modelResponse", {})
                .get("message", "")
            )
            chunk = "\n" + chunk

        yield chunk
    logger.info(
        f"""{{
        "model": "{model}",
        "prompt": "{prompt}",
        "response_text": "{response_text}"
    }}"""
    )


async def extract_messages_and_images(messages: list[ChatMessage]):
    texts = []
    # base64_images = []
    image_paths = []
    roles = []
    for message in messages:
        role = message.role
        content = message.content
        roles.append(role)
        if isinstance(content, str):
            texts.append(content)
        elif isinstance(content, list):
            for item in content:
                message_type = item["type"]
                if message_type == "text":
                    texts.append(item["text"])
                elif message_type == "image_url":
                    base64_image = item["image_url"]["url"]
                    image_path = await save_base64_image(base64_image)
                    image_paths.append(image_path)
                else:
                    raise ValueError("Invalid message content type")
    messages = []
    for text, role in zip(texts, roles):
        messages.append(ChatMessage(role=role, content=text))
    return messages, image_paths


async def summarize_a_title(
    conversation_str: str, conversation_id, client_idx, api_key, client
) -> str:
    prompt = f"""\
This a is a conversation:
{conversation_str}
- Just give a short title(no more than 5 words) for it directly in language the conversation use.
- Chinese title is preferred.
Title:"""
    response_text = ""
    model = "gpt-4o-mini"
    async for text in client.stream_message(
        prompt,
        conversation_id,
        model,
        client_type="plus",
        client_idx=client_idx,
        attachments=[],
        files=[],
        call_back=None,
        api_key=api_key,
        file_paths=[],
    ):
        response_text += text
    return response_text


async def listen_for_disconnect(request: Request) -> None:
    """Returns if a disconnect message is received"""
    while True:
        message = await request.receive()
        if message["type"] == "http.disconnect":
            break


def with_cancellation(handler_func):
    """Decorator that allows a route handler to be cancelled by client
    disconnections.

    This does _not_ use request.is_disconnected, which does not work with
    middleware. Instead this follows the pattern from
    starlette.StreamingResponse, which simultaneously awaits on two tasks- one
    to wait for an http disconnect message, and the other to do the work that we
    want done. When the first task finishes, the other is cancelled.

    A core assumption of this method is that the body of the request has already
    been read. This is a safe assumption to make for fastapi handlers that have
    already parsed the body of the request into a pydantic model for us.
    This decorator is unsafe to use elsewhere, as it will consume and throw away
    all incoming messages for the request while it looks for a disconnect
    message.

    In the case where a `StreamingResponse` is returned by the handler, this
    wrapper will stop listening for disconnects and instead the response object
    will start listening for disconnects.
    """

    # Functools.wraps is required for this wrapper to appear to fastapi as a
    # normal route handler, with the correct request type hinting.
    @functools.wraps(handler_func)
    async def wrapper(*args, **kwargs):
        # The request is either the second positional arg or `raw_request`
        request = args[1] if len(args) > 1 else kwargs["raw_request"]

        handler_task = asyncio.create_task(handler_func(*args, **kwargs))
        cancellation_task = asyncio.create_task(listen_for_disconnect(request))

        done, pending = await asyncio.wait(
            [handler_task, cancellation_task], return_when=asyncio.FIRST_COMPLETED
        )
        for task in pending:
            task.cancel()

        if handler_task in done:
            return handler_task.result()
        return None

    return wrapper
