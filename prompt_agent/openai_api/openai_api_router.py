import asyncio
import json
import time
import uuid
from datetime import datetime
from functools import partial
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from loguru import logger

from prompt_agent.agent import get_prompt_agent
from prompt_agent.configs import (DEFAULT_RETRIVAL_COUNT,
                                  POE_OPENAI_LIKE_API_KEY)
from prompt_agent.models.chat_message import RequestType
from prompt_agent.openai_api.schemas import ChatCompletionRequest, ChatMessage
from prompt_agent.prompts import OPTIMIZE_PROMPT, RAG_REFER_PROMPT
from prompt_agent.redis_manager.api_key_manager import get_api_key_manager
from prompt_agent.utils.usage_tracking import (UsageTracker,
                                               create_background_task,
                                               create_chat_message_record,
                                               estimate_tokens)
from prompt_agent.vector_db.prompt_vector_db import get_prompt_vector_db

# Add this constant at the top of the file after the imports
VALID_API_KEY = POE_OPENAI_LIKE_API_KEY

router = APIRouter()


# API Key validation dependency
async def validate_api_key(authorization: str = Header(None)) -> str:
    """
    API key validation dependency
    Returns the validated API key or raises HTTPException
    """
    # Extract API key from Authorization header
    api_key = None
    if authorization:
        if authorization.startswith("Bearer"):
            api_key = authorization.replace("Bearer", "").strip()

    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid Authorization header. Format should be 'Bearer YOUR_API_KEY'",
        )

    # Check if it's the fallback API key
    if api_key == VALID_API_KEY:
        # Allow the original fallback key to pass through
        logger.debug(f"Using fallback API key")
        return api_key

    # Use APIKeyManager for validation and usage tracking
    api_key_manager = get_api_key_manager()

    # Validate API key exists and is not deleted/expired
    is_valid = await api_key_manager.is_api_key_valid(api_key)
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid or expired API key")

    # Increment usage (this also handles activation on first use)
    usage_result = await api_key_manager.increment_usage(api_key)
    if not usage_result["success"]:
        # Get detailed usage info for better error message
        usage_info = await api_key_manager.get_usage_info(api_key)

        # Calculate wait time information
        time_until_reset = usage_info.get("time_until_reset", 0)
        if time_until_reset > 0:
            hours = time_until_reset // 3600
            minutes = (time_until_reset % 3600) // 60
            seconds = time_until_reset % 60

            if hours > 0:
                wait_time_str = f"{hours}小时{minutes}分钟"
            elif minutes > 0:
                wait_time_str = f"{minutes}分钟{seconds}秒"
            else:
                wait_time_str = f"{seconds}秒"

            current_usage = usage_info.get("current_period_usage", 0)
            usage_limit = usage_info.get("usage_limit", 0)

            detail_message = (
                f"使用次数已达限制 ({current_usage}/{usage_limit})。" f"请等待 {wait_time_str} 后重试。"
            )
        else:
            detail_message = usage_result["message"]

        raise HTTPException(
            status_code=429,
            detail=detail_message,
            headers={"Retry-After": str(time_until_reset)},
        )

    logger.info(
        f"API key {api_key[:10]}... used. Usage info: {usage_result.get('usage_info', {})}"
    )

    return api_key


async def _async_resp_generator(original_generator, model: str):
    i = 0
    response_text = ""
    first_chunk = True
    async for data in original_generator:
        response_text += data
        chunk = {
            "id": i,
            "object": "chat.completion.chunk",
            "created": time.time(),
            "model": model,
            "choices": [
                {
                    "delta": {
                        "content": f"{data}",
                        **(
                            {"role": "assistant"} if first_chunk else {}
                        ),  # 只在第一个chunk添加role
                    }
                }
            ],
        }
        first_chunk = False

        yield f"data: {json.dumps(chunk)}\n\n"
        i += 1

    yield f"data: {json.dumps({'choices':[{'index': 0, 'delta': {}, 'logprobs': None, 'finish_reason': 'stop'}]})}\n\n"
    yield "data: [DONE]\n\n"


async def streaming_message(request: ChatCompletionRequest, api_key: str):
    """
    Process streaming message request with validated API key
    Note: API key validation and usage tracking is now handled by the dependency
    """
    model = request.model
    messages = request.messages
    _prompt_agent = get_prompt_agent()

    # Convert ChatMessage objects to dict format expected by optimize_prompt
    messages_dict = [
        {"role": msg.role, "content": str(msg.content)} for msg in messages
    ]

    return _prompt_agent.optimize_prompt(
        messages=messages_dict,
        stream=request.stream or False,
        enable_vector_db_retrival=request.enable_retrival or False,
        collection_name=request.collection_name or "",
    )


@router.post("/chat/completions")
async def chat_completions(
    request_body: ChatCompletionRequest,
    fastapi_request: Request,
    api_key: str = Depends(validate_api_key),
):
    """
    Chat completions endpoint with API key validation dependency and usage tracking
    """
    if not request_body.messages:
        raise HTTPException(status_code=400, detail="No messages provided.")

    # Prepare request parameters for tracking
    request_params = {
        "max_tokens": request_body.max_tokens,
        "temperature": request_body.temperature,
        "stream": request_body.stream,
        "enable_retrieval": request_body.enable_retrival,
        "collection_name": request_body.collection_name,
    }

    # Initialize usage tracker explicitly (no context manager)
    tracker = UsageTracker(
        api_key=api_key,
        request_type=RequestType.CHAT_COMPLETION,
        model=request_body.model,
        request_params=request_params,
        request=fastapi_request,
    )

    try:
        # Extract user prompt from messages for token estimation
        # user_prompt = ""
        # for msg in request_body.messages:
        #     if msg.role == "user":
        #         user_prompt += str(msg.content) + "\n"
        # user_prompt = user_prompt.strip()
        user_prompt = request_body.messages[-1].content

        # For token estimation, we'll estimate based on the user prompt
        # The actual optimization is handled by streaming_message function
        # This is a reasonable approximation for billing purposes

        # Estimate input tokens based on user prompt (approximation for billing)
        input_tokens = estimate_tokens(user_prompt)
        tracker.set_tokens(input_tokens=input_tokens)

        # Get response from agent
        resp_content = await streaming_message(request_body, api_key)

        if request_body.stream:
            # For streaming responses, we need to collect the response text
            async def tracked_stream_generator():
                response_text = ""
                try:
                    async for chunk in _async_resp_generator(
                        resp_content, request_body.model
                    ):
                        # Extract content from chunk to build response text
                        try:
                            chunk_data = json.loads(chunk.replace("data: ", "").strip())
                            if (
                                "choices" in chunk_data
                                and len(chunk_data["choices"]) > 0
                            ):
                                delta = chunk_data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    response_text += content
                        except (json.JSONDecodeError, KeyError):
                            pass

                        yield chunk

                    # Streaming completed successfully
                    tracker.request_end_time = (
                        tracker.request_end_time or datetime.now()
                    )

                except Exception as stream_error:
                    # Handle streaming errors
                    tracker.set_error(
                        str(stream_error), getattr(stream_error, "status_code", None)
                    )
                    tracker.request_end_time = datetime.now()
                    raise
                finally:
                    # Record final response data and set chat details in tracker
                    output_tokens = estimate_tokens(response_text)
                    tracker.set_tokens(output_tokens=output_tokens)
                    tracker.set_chat_details(
                        user_prompt=user_prompt,
                        optimized_prompt=user_prompt,  # Simplified: using user_prompt as approximation
                        assistant_response=response_text,
                    )

                    # Explicitly create background task to record usage
                    logger.info(
                        f"Creating background task to record usage for request {tracker.request_id}"
                    )
                    create_background_task(
                        tracker.record_usage(), f"usage_record_{tracker.request_id}"
                    )

                    # Explicitly create background task to record chat message
                    logger.info(
                        f"Creating background task to record chat message for request {tracker.request_id}"
                    )
                    create_background_task(
                        create_chat_message_record(
                            request_id=tracker.request_id,
                            api_key=api_key,
                            model=request_body.model,
                            user_prompt=user_prompt,
                            assistant_response=response_text,
                            optimized_prompt=user_prompt,  # Simplified: using user_prompt as approximation
                            request_params=request_params,
                            client_ip=tracker.client_ip,
                            user_agent=tracker.user_agent,
                        ),
                        f"chat_message_{tracker.request_id}",
                    )

            return StreamingResponse(
                tracked_stream_generator(),
                media_type="text/event-stream",
            )
        else:
            # Non-streaming response (not implemented in original code)
            response_content = "not implemented"
            output_tokens = estimate_tokens(response_content)
            tracker.set_tokens(output_tokens=output_tokens)
            tracker.set_chat_details(
                user_prompt=user_prompt,
                optimized_prompt=user_prompt,  # Simplified: using user_prompt as approximation
                assistant_response=response_content,
            )

            # Set end time for non-streaming response
            tracker.request_end_time = datetime.now()

            # Explicitly create background task to record usage
            logger.info(
                f"Creating background task to record usage for request {tracker.request_id}"
            )
            create_background_task(
                tracker.record_usage(), f"usage_record_{tracker.request_id}"
            )

            # Explicitly create background task to record chat message
            logger.info(
                f"Creating background task to record chat message for request {tracker.request_id}"
            )
            create_background_task(
                create_chat_message_record(
                    request_id=tracker.request_id,
                    api_key=api_key,
                    model=request_body.model,
                    user_prompt=user_prompt,
                    assistant_response=response_content,
                    optimized_prompt=user_prompt,  # Simplified: using user_prompt as approximation
                    request_params=request_params,
                    client_ip=tracker.client_ip,
                    user_agent=tracker.user_agent,
                ),
                f"chat_message_{tracker.request_id}",
            )

            return {
                "id": tracker.request_id,
                "object": "chat.completion",
                "created": time.time(),
                "model": request_body.model,
                "choices": [
                    {"message": ChatMessage(role="assistant", content=response_content)}
                ],
            }

    except Exception as e:
        # Set error information in tracker and record the failed request
        tracker.set_error(str(e), getattr(e, "status_code", None))
        tracker.request_end_time = datetime.now()

        # Explicitly create background task to record the error
        logger.error(f"Request {tracker.request_id} failed with error: {str(e)}")
        logger.info(
            f"Creating background task to record failed usage for request {tracker.request_id}"
        )
        create_background_task(
            tracker.record_usage(), f"usage_record_error_{tracker.request_id}"
        )
        raise
