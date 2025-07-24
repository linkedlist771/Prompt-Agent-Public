from enum import Enum
from typing import Any, Dict, Optional

import numpy as np
from loguru import logger
from tortoise import fields

from prompt_agent.models.base import CRUDBase


class RequestStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"


class RequestType(str, Enum):
    CHAT_COMPLETION = "chat_completion"
    EMBEDDINGS = "embeddings"
    OTHER = "other"


class ChatMessage(CRUDBase):
    # Request information
    request_id = fields.CharField(max_length=100, unique=True)
    api_key = fields.CharField(max_length=100, db_index=True)
    timestamp = fields.DatetimeField(auto_now_add=True, db_index=True)

    # Request details
    model = fields.CharField(max_length=100, default="mock-gpt-model")
    user_prompt = fields.TextField()
    optimized_prompt = fields.TextField(null=True)  # The enhanced prompt sent to LLM
    assistant_response = fields.TextField()

    # Request parameters
    max_tokens = fields.IntField(null=True)
    temperature = fields.FloatField(null=True)
    stream = fields.BooleanField(default=False)
    enable_retrieval = fields.BooleanField(default=False)
    collection_name = fields.CharField(max_length=100, null=True)

    # Metadata
    ip_address = fields.CharField(max_length=45, null=True)  # IPv6 compatible
    user_agent = fields.TextField(null=True)

    class Meta:
        table = "chat_messages"
        ordering = ["-timestamp"]


class UsageRecord(CRUDBase):
    # Request identification
    request_id = fields.CharField(max_length=100, unique=True, db_index=True)
    api_key = fields.CharField(max_length=100, db_index=True)
    timestamp = fields.DatetimeField(auto_now_add=True, db_index=True)

    # Request details
    request_type = fields.CharEnumField(
        RequestType, default=RequestType.CHAT_COMPLETION
    )
    model = fields.CharField(max_length=100)
    status = fields.CharEnumField(RequestStatus, default=RequestStatus.SUCCESS)

    # Timing information
    request_start_time = fields.DatetimeField(db_index=True)
    request_end_time = fields.DatetimeField(null=True)
    response_time_ms = fields.IntField(null=True)  # Response time in milliseconds

    # Token usage (estimated)
    input_tokens = fields.IntField(null=True)
    output_tokens = fields.IntField(null=True)
    total_tokens = fields.IntField(null=True)

    # Cost estimation (if applicable)
    estimated_cost_usd = fields.DecimalField(max_digits=10, decimal_places=6, null=True)

    # Request parameters
    max_tokens = fields.IntField(null=True)
    temperature = fields.FloatField(null=True)
    stream = fields.BooleanField(default=False)
    enable_retrieval = fields.BooleanField(default=False)
    collection_name = fields.CharField(max_length=100, null=True)

    # Response information
    error_message = fields.TextField(null=True)
    error_code = fields.CharField(max_length=50, null=True)

    # Network information
    ip_address = fields.CharField(max_length=45, null=True)
    user_agent = fields.TextField(null=True)

    # Additional metadata
    metadata = fields.JSONField(
        default=lambda: {}
    )  # For storing additional custom data

    class Meta:
        table = "usage_records"
        ordering = ["-timestamp"]

    @classmethod
    async def get_usage_stats(
        cls, api_key: Optional[str] = None, days: int = 30
    ) -> Dict[str, Any]:
        """Get usage statistics for a specific API key or overall"""
        from datetime import datetime, timedelta

        from tortoise.functions import Avg, Sum

        start_date = datetime.now() - timedelta(days=days)
        query = cls.filter(timestamp__gte=start_date)

        if api_key:
            query = query.filter(api_key=api_key)

        # Basic counts
        total_requests = await query.count()
        successful_requests = await query.filter(status=RequestStatus.SUCCESS).count()
        failed_requests = await query.filter(status=RequestStatus.ERROR).count()

        # Token usage - calculate manually since Tortoise ORM aggregate behavior varies
        records = await query.all()
        total_input_tokens = sum(r.input_tokens or 0 for r in records)
        total_output_tokens = sum(r.output_tokens or 0 for r in records)
        total_tokens_sum = sum(r.total_tokens or 0 for r in records)

        # Average response time
        response_times = [
            r.response_time_ms for r in records if r.response_time_ms is not None
        ]
        avg_response_time = (
            sum(response_times) / len(response_times) if response_times else 0
        )

        return {
            "period_days": days,
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "success_rate": (successful_requests / total_requests * 100)
            if total_requests > 0
            else 0,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_tokens": total_tokens_sum,
            "avg_response_time_ms": avg_response_time,
        }
