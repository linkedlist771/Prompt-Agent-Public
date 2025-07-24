import asyncio
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import Request
from loguru import logger

from prompt_agent.models.chat_message import (ChatMessage, RequestStatus,
                                              RequestType, UsageRecord)


async def _safe_background_task(coro, task_name: str):
    """Wrapper for background tasks with error handling"""
    try:
        await coro
    except Exception as e:
        logger.error(f"Background task '{task_name}' failed: {str(e)}")


def create_background_task(coro, task_name: str = "background_task"):
    """Create a background task with error handling"""
    return asyncio.create_task(_safe_background_task(coro, task_name))


def estimate_tokens(text: str) -> int:
    """
    Simple token estimation for text.
    This is a rough approximation: ~4 characters per token for English text.
    For more accurate estimation, you could integrate with tiktoken or similar libraries.
    """
    if not text:
        return 0
    return max(1, len(text) // 4)


def get_client_ip(request: Request) -> Optional[str]:
    """Extract client IP address from request headers"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    return getattr(request.client, "host", None) if request.client else None


def get_user_agent(request: Request) -> Optional[str]:
    """Extract user agent from request headers"""
    return request.headers.get("User-Agent")


async def create_usage_record(
    request_id: str,
    api_key: str,
    request_type: RequestType,
    model: str,
    request_start_time: datetime,
    request_end_time: Optional[datetime] = None,
    status: RequestStatus = RequestStatus.SUCCESS,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
    error_message: Optional[str] = None,
    error_code: Optional[str] = None,
    request_params: Optional[Dict] = None,
    client_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    metadata: Optional[Dict] = None,
) -> UsageRecord:
    """
    Create a usage record in the database
    """
    try:
        # Calculate response time
        response_time_ms = None
        if request_end_time and request_start_time:
            response_time_ms = int(
                (request_end_time - request_start_time).total_seconds() * 1000
            )

        # Calculate total tokens
        total_tokens = None
        if input_tokens is not None and output_tokens is not None:
            total_tokens = input_tokens + output_tokens
        elif input_tokens is not None:
            total_tokens = input_tokens
        elif output_tokens is not None:
            total_tokens = output_tokens

        # Extract request parameters
        max_tokens = None
        temperature = None
        stream = False
        enable_retrieval = False
        collection_name = None

        if request_params:
            max_tokens = request_params.get("max_tokens")
            temperature = request_params.get("temperature")
            stream = request_params.get("stream", False)
            enable_retrieval = request_params.get("enable_retrieval", False)
            collection_name = request_params.get("collection_name")

        # Estimate cost (placeholder - implement actual cost calculation based on your pricing)
        estimated_cost_usd = None
        if total_tokens:
            # Example: $0.002 per 1K tokens (adjust based on your actual pricing)
            estimated_cost_usd = (total_tokens / 1000) * 0.002

        usage_record = await UsageRecord.create_item(
            request_id=request_id,
            api_key=api_key,
            request_type=request_type,
            model=model,
            status=status,
            request_start_time=request_start_time,
            request_end_time=request_end_time,
            response_time_ms=response_time_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=estimated_cost_usd,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=stream,
            enable_retrieval=enable_retrieval,
            collection_name=collection_name,
            error_message=error_message,
            error_code=error_code,
            ip_address=client_ip,
            user_agent=user_agent,
            metadata=metadata or {},
        )

        logger.info(f"Usage record created: {request_id} for API key {api_key[:10]}...")
        return usage_record

    except Exception as e:
        logger.error(f"Failed to create usage record for {request_id}: {str(e)}")
        raise


async def create_chat_message_record(
    request_id: str,
    api_key: str,
    model: str,
    user_prompt: str,
    assistant_response: str,
    optimized_prompt: Optional[str] = None,
    request_params: Optional[Dict] = None,
    client_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> ChatMessage:
    """
    Create a chat message record in the database
    """
    try:
        # Extract request parameters
        max_tokens = None
        temperature = None
        stream = False
        enable_retrieval = False
        collection_name = None

        if request_params:
            max_tokens = request_params.get("max_tokens")
            temperature = request_params.get("temperature")
            stream = request_params.get("stream", False)
            enable_retrieval = request_params.get("enable_retrieval", False)
            collection_name = request_params.get("collection_name")

        chat_message = await ChatMessage.create_item(
            request_id=request_id,
            api_key=api_key,
            model=model,
            user_prompt=user_prompt,
            optimized_prompt=optimized_prompt,
            assistant_response=assistant_response,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=stream,
            enable_retrieval=enable_retrieval,
            collection_name=collection_name,
            ip_address=client_ip,
            user_agent=user_agent,
        )

        logger.info(
            f"Chat message record created: {request_id} for API key {api_key[:10]}..."
        )
        return chat_message

    except Exception as e:
        logger.error(f"Failed to create chat message record for {request_id}: {str(e)}")
        raise


class UsageTracker:
    """
    Context manager for tracking API usage
    """

    def __init__(
        self,
        api_key: str,
        request_type: RequestType,
        model: str,
        request_params: Optional[Dict] = None,
        request: Optional[Request] = None,
    ):
        self.request_id = str(uuid.uuid4())
        self.api_key = api_key
        self.request_type = request_type
        self.model = model
        self.request_params = request_params or {}
        self.request_start_time = datetime.now()
        self.request_end_time: Optional[datetime] = None
        self.status = RequestStatus.SUCCESS
        self.error_message: Optional[str] = None
        self.error_code: Optional[str] = None
        self.input_tokens: Optional[int] = None
        self.output_tokens: Optional[int] = None
        self.metadata: Dict = {}

        # Chat message fields
        self.user_prompt: Optional[str] = None
        self.optimized_prompt: Optional[str] = None
        self.assistant_response: Optional[str] = None

        # Extract client information
        self.client_ip = get_client_ip(request) if request else None
        self.user_agent = get_user_agent(request) if request else None

    async def __aenter__(self):
        """Enter the async context manager"""
        logger.debug(f"Starting usage tracking for request {self.request_id}")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the async context manager and record usage"""
        self.request_end_time = datetime.now()

        if exc_type is not None:
            # An exception occurred
            self.status = RequestStatus.ERROR
            self.error_message = str(exc_val) if exc_val else "Unknown error"
            if hasattr(exc_val, "status_code"):
                self.error_code = str(exc_val.status_code)

        # Record usage as background task (non-blocking)
        create_background_task(self.record_usage(), "usage_record")

    async def record_usage(self):
        """Record the usage in the database"""
        try:
            # Record usage statistics
            await create_usage_record(
                request_id=self.request_id,
                api_key=self.api_key,
                request_type=self.request_type,
                model=self.model,
                request_start_time=self.request_start_time,
                request_end_time=self.request_end_time,
                status=self.status,
                input_tokens=self.input_tokens,
                output_tokens=self.output_tokens,
                error_message=self.error_message,
                error_code=self.error_code,
                request_params=self.request_params,
                client_ip=self.client_ip,
                user_agent=self.user_agent,
                metadata=self.metadata,
            )

            # # Record chat message if we have the conversation details
            # if self.user_prompt and self.assistant_response:
            #     await create_chat_message_record(
            #         request_id=self.request_id,
            #         api_key=self.api_key,
            #         model=self.model,
            #         user_prompt=self.user_prompt,
            #         optimized_prompt=self.optimized_prompt,
            #         assistant_response=self.assistant_response,
            #         request_params=self.request_params,
            #         client_ip=self.client_ip,
            #         user_agent=self.user_agent,
            #     )
        except Exception as e:
            logger.error(f"Failed to record usage for {self.request_id}: {str(e)}")

    def set_chat_details(
        self,
        user_prompt: str,
        optimized_prompt: Optional[str] = None,
        assistant_response: str = "",
    ):
        """Set chat conversation details"""
        self.user_prompt = user_prompt
        self.optimized_prompt = optimized_prompt
        self.assistant_response = assistant_response

    def set_tokens(
        self, input_tokens: Optional[int] = None, output_tokens: Optional[int] = None
    ):
        """Set token counts"""
        if input_tokens is not None:
            self.input_tokens = input_tokens
        if output_tokens is not None:
            self.output_tokens = output_tokens

    def set_error(self, error_message: str, error_code: Optional[str] = None):
        """Set error information"""
        self.status = RequestStatus.ERROR
        self.error_message = error_message
        self.error_code = error_code

    def add_metadata(self, key: str, value):
        """Add metadata"""
        self.metadata[key] = value
