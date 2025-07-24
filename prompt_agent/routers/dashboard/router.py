import hashlib
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles
from fastapi import (APIRouter, Depends, Form, HTTPException, Query, Request,
                     Response)
from fastapi.responses import HTMLResponse, RedirectResponse
from loguru import logger
from pydantic import BaseModel, Field

from prompt_agent.configs import DASHBOARD_PASSWORD, DASHBOARD_USERNAME
from prompt_agent.models.chat_message import (ChatMessage, RequestStatus,
                                              RequestType, UsageRecord)

router = APIRouter()

# Simple in-memory session storage (in production, use Redis or database)
active_sessions = {}


# Authentication models
class LoginRequest(BaseModel):
    username: str
    password: str


def create_session(username: str) -> str:
    """Create a new session for the user"""
    session_id = str(uuid.uuid4())
    active_sessions[session_id] = {
        "username": username,
        "created_at": datetime.now(),
        "last_accessed": datetime.now(),
    }
    return session_id


def get_session(session_id: str) -> Optional[Dict]:
    """Get session data if valid"""
    if session_id in active_sessions:
        session = active_sessions[session_id]
        # Update last accessed time
        session["last_accessed"] = datetime.now()
        return session
    return None


def delete_session(session_id: str):
    """Delete a session"""
    if session_id in active_sessions:
        del active_sessions[session_id]


def clean_expired_sessions():
    """Clean up expired sessions (older than 24 hours)"""
    current_time = datetime.now()
    expired_sessions = []
    for session_id, session in active_sessions.items():
        if current_time - session["last_accessed"] > timedelta(hours=24):
            expired_sessions.append(session_id)

    for session_id in expired_sessions:
        del active_sessions[session_id]


def get_current_user(request: Request) -> Optional[str]:
    """Get current authenticated user from session"""
    session_id = request.cookies.get("dashboard_session")
    if session_id:
        session = get_session(session_id)
        if session:
            return session["username"]
    return None


def require_auth(request: Request) -> str:
    """Dependency to require authentication"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


# Authentication endpoints
@router.post("/auth/login")
async def login(username: str = Form(...), password: str = Form(...)):
    """Login endpoint"""
    clean_expired_sessions()  # Clean up expired sessions

    if username == DASHBOARD_USERNAME and password == DASHBOARD_PASSWORD:
        session_id = create_session(username)
        response = RedirectResponse(url="/dashboard", status_code=302)
        response.set_cookie(
            key="dashboard_session",
            value=session_id,
            max_age=86400,  # 24 hours
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax",
        )
        return response
    else:
        # Return to login page with error
        return RedirectResponse(
            url="/dashboard?error=invalid_credentials", status_code=302
        )


@router.post("/auth/logout")
async def logout(request: Request):
    """Logout endpoint"""
    session_id = request.cookies.get("dashboard_session")
    if session_id:
        delete_session(session_id)

    response = RedirectResponse(url="/dashboard", status_code=302)
    response.delete_cookie("dashboard_session")
    return response


@router.get("/auth/check")
async def check_auth(request: Request):
    """Check authentication status"""
    user = get_current_user(request)
    return {"authenticated": user is not None, "username": user}


# Dashboard HTML serving
@router.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """Serve the dashboard HTML"""
    try:
        dashboard_path = (
            Path(__file__).parent.parent.parent / "static" / "dashboard.html"
        )
        async with aiofiles.open(dashboard_path, mode="r", encoding="utf-8") as f:
            html_content = await f.read()
        return HTMLResponse(content=html_content)
    except Exception as e:
        logger.error(f"Error serving dashboard HTML: {str(e)}")
        raise HTTPException(status_code=500, detail="Dashboard not available")


# Response models
class ChatMessageResponse(BaseModel):
    id: int
    request_id: str
    api_key: str
    timestamp: datetime
    model: str
    user_prompt: str
    optimized_prompt: Optional[str]
    assistant_response: str
    max_tokens: Optional[int]
    temperature: Optional[float]
    stream: bool
    enable_retrieval: bool
    collection_name: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]

    class Config:
        from_attributes = True


class UsageRecordResponse(BaseModel):
    id: int
    request_id: str
    api_key: str
    timestamp: datetime
    request_type: RequestType
    model: str
    status: RequestStatus
    request_start_time: datetime
    request_end_time: Optional[datetime]
    response_time_ms: Optional[int]
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    total_tokens: Optional[int]
    estimated_cost_usd: Optional[float]
    error_message: Optional[str]
    error_code: Optional[str]
    ip_address: Optional[str]

    class Config:
        from_attributes = True


class PaginatedResponse(BaseModel):
    items: List[Dict]
    total: int
    page: int
    page_size: int
    total_pages: int


class UsageStatsResponse(BaseModel):
    period_days: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    success_rate: float
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    avg_response_time_ms: float


class ApiKeyUsageResponse(BaseModel):
    api_key: str
    usage_stats: UsageStatsResponse
    recent_activity: List[UsageRecordResponse]


class DashboardStatsResponse(BaseModel):
    overall_stats: UsageStatsResponse
    top_api_keys: List[Dict[str, Any]]
    hourly_activity: List[Dict[str, Any]]
    model_usage: List[Dict[str, Any]]
    error_breakdown: List[Dict[str, Any]]


# Chat Messages Endpoints
@router.get("/chat-messages", response_model=PaginatedResponse)
async def get_chat_messages(
    request: Request,
    api_key: Optional[str] = Query(None, description="Filter by API key"),
    model: Optional[str] = Query(None, description="Filter by model"),
    search: Optional[str] = Query(None, description="Search in prompts and responses"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    order_by: str = Query("-timestamp", description="Order by field"),
    current_user: str = Depends(require_auth),
):
    """Get chat messages with filtering and pagination"""
    try:
        # Build filter conditions
        filters = {}
        if api_key:
            filters["api_key"] = api_key
        if model:
            filters["model"] = model
        if start_date:
            filters["timestamp__gte"] = start_date
        if end_date:
            filters["timestamp__lte"] = end_date

        # Calculate offset
        offset = (page - 1) * page_size

        # Get messages
        if search:
            # Use search functionality
            messages = await ChatMessage.search_items(
                search_fields=["user_prompt", "assistant_response"],
                search_term=search,
                skip=offset,
                limit=page_size,
                order_by=order_by,
            )
            # For search, we need to count differently
            total = await ChatMessage.get_count(**filters)
        else:
            messages = await ChatMessage.get_multi(
                skip=offset, limit=page_size, order_by=order_by, **filters
            )
            total = await ChatMessage.get_count(**filters)

        # Convert to response format
        items = []
        for msg in messages:
            items.append(
                {
                    "id": msg.id,
                    "request_id": msg.request_id,
                    "api_key": msg.api_key[:10] + "..."
                    if len(msg.api_key) > 10
                    else msg.api_key,
                    "timestamp": msg.timestamp,
                    "model": msg.model,
                    "user_prompt": msg.user_prompt[:200] + "..."
                    if len(msg.user_prompt) > 200
                    else msg.user_prompt,
                    "optimized_prompt": msg.optimized_prompt[:200] + "..."
                    if msg.optimized_prompt and len(msg.optimized_prompt) > 200
                    else msg.optimized_prompt,
                    "assistant_response": msg.assistant_response[:200] + "..."
                    if len(msg.assistant_response) > 200
                    else msg.assistant_response,
                    "max_tokens": msg.max_tokens,
                    "temperature": msg.temperature,
                    "stream": msg.stream,
                    "enable_retrieval": msg.enable_retrieval,
                    "collection_name": msg.collection_name,
                    "ip_address": msg.ip_address,
                }
            )

        total_pages = (total + page_size - 1) // page_size

        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    except Exception as e:
        logger.error(f"Error fetching chat messages: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching chat messages: {str(e)}"
        )


@router.get("/chat-messages/{request_id}", response_model=ChatMessageResponse)
async def get_chat_message_detail(
    request_id: str, current_user: str = Depends(require_auth)
):
    """Get detailed chat message by request ID"""
    try:
        message = await ChatMessage.get_or_none(request_id=request_id)
        if not message:
            raise HTTPException(status_code=404, detail="Chat message not found")

        return ChatMessageResponse.from_orm(message)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching chat message detail: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching chat message detail: {str(e)}"
        )


# Usage Records Endpoints
@router.get("/usage-records", response_model=PaginatedResponse)
async def get_usage_records(
    api_key: Optional[str] = Query(None, description="Filter by API key"),
    model: Optional[str] = Query(None, description="Filter by model"),
    status: Optional[RequestStatus] = Query(None, description="Filter by status"),
    request_type: Optional[RequestType] = Query(
        None, description="Filter by request type"
    ),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    order_by: str = Query("-timestamp", description="Order by field"),
    current_user: str = Depends(require_auth),
):
    """Get usage records with filtering and pagination"""
    try:
        # Build filter conditions
        filters = {}
        if api_key:
            filters["api_key"] = api_key
        if model:
            filters["model"] = model
        if status:
            filters["status"] = status
        if request_type:
            filters["request_type"] = request_type
        if start_date:
            filters["timestamp__gte"] = start_date
        if end_date:
            filters["timestamp__lte"] = end_date

        # Calculate offset
        offset = (page - 1) * page_size

        # Get records
        records = await UsageRecord.get_multi(
            skip=offset, limit=page_size, order_by=order_by, **filters
        )
        total = await UsageRecord.get_count(**filters)

        # Convert to response format
        items = []
        for record in records:
            items.append(
                {
                    "id": record.id,
                    "request_id": record.request_id,
                    "api_key": record.api_key[:10] + "..."
                    if len(record.api_key) > 10
                    else record.api_key,
                    "timestamp": record.timestamp,
                    "request_type": record.request_type,
                    "model": record.model,
                    "status": record.status,
                    "response_time_ms": record.response_time_ms,
                    "input_tokens": record.input_tokens,
                    "output_tokens": record.output_tokens,
                    "total_tokens": record.total_tokens,
                    "estimated_cost_usd": record.estimated_cost_usd,
                    "error_message": record.error_message[:100] + "..."
                    if record.error_message and len(record.error_message) > 100
                    else record.error_message,
                    "ip_address": record.ip_address,
                }
            )

        total_pages = (total + page_size - 1) // page_size

        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    except Exception as e:
        logger.error(f"Error fetching usage records: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching usage records: {str(e)}"
        )


# Statistics Endpoints
@router.get("/usage-stats", response_model=UsageStatsResponse)
async def get_usage_stats(
    api_key: Optional[str] = Query(None, description="Filter by API key"),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: str = Depends(require_auth),
):
    """Get usage statistics for a specific API key or overall"""
    try:
        stats = await UsageRecord.get_usage_stats(api_key=api_key, days=days)
        return UsageStatsResponse(**stats)

    except Exception as e:
        logger.error(f"Error fetching usage stats: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching usage stats: {str(e)}"
        )


@router.get("/api-key-usage", response_model=List[ApiKeyUsageResponse])
async def get_api_key_usage(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    limit: int = Query(10, ge=1, le=50, description="Number of top API keys to return"),
    current_user: str = Depends(require_auth),
):
    """Get usage statistics for top API keys"""
    try:
        # Get all API keys with usage in the period
        start_date = datetime.now() - timedelta(days=days)
        records = await UsageRecord.filter(timestamp__gte=start_date).all()
        api_keys = list(set(record.api_key for record in records))

        results = []
        for api_key in api_keys[:limit]:
            # Get stats for this API key
            stats = await UsageRecord.get_usage_stats(api_key=api_key, days=days)

            # Get recent activity
            recent_records = await UsageRecord.get_multi(
                api_key=api_key, skip=0, limit=5, order_by="-timestamp"
            )

            recent_activity = [
                UsageRecordResponse.from_orm(record) for record in recent_records
            ]

            results.append(
                ApiKeyUsageResponse(
                    api_key=api_key[:10] + "..." if len(api_key) > 10 else api_key,
                    usage_stats=UsageStatsResponse(**stats),
                    recent_activity=recent_activity,
                )
            )

        # Sort by total requests
        results.sort(key=lambda x: x.usage_stats.total_requests, reverse=True)

        return results

    except Exception as e:
        logger.error(f"Error fetching API key usage: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching API key usage: {str(e)}"
        )


@router.get("/dashboard-stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    days: int = Query(7, ge=1, le=365, description="Number of days to analyze"),
    current_user: str = Depends(require_auth),
):
    """Get comprehensive dashboard statistics"""
    try:
        # Overall stats
        overall_stats = await UsageRecord.get_usage_stats(days=days)

        # Top API keys by usage
        start_date = datetime.now() - timedelta(days=days)
        records = await UsageRecord.filter(timestamp__gte=start_date).all()

        # Group by API key
        api_key_usage = {}
        for record in records:
            key = (
                record.api_key[:10] + "..."
                if len(record.api_key) > 10
                else record.api_key
            )
            if key not in api_key_usage:
                api_key_usage[key] = {"count": 0, "tokens": 0}
            api_key_usage[key]["count"] += 1
            api_key_usage[key]["tokens"] += record.total_tokens or 0

        top_api_keys = [
            {"api_key": k, "requests": v["count"], "tokens": v["tokens"]}
            for k, v in sorted(
                api_key_usage.items(), key=lambda x: x[1]["count"], reverse=True
            )[:10]
        ]

        # Hourly activity (last 24 hours)
        last_24h = datetime.now() - timedelta(hours=24)
        hourly_records = await UsageRecord.filter(timestamp__gte=last_24h).all()

        hourly_activity = {}
        for record in hourly_records:
            hour = record.timestamp.strftime("%H:00")
            hourly_activity[hour] = hourly_activity.get(hour, 0) + 1

        hourly_activity_list = [
            {"hour": hour, "requests": count}
            for hour, count in sorted(hourly_activity.items())
        ]

        # Model usage
        model_usage = {}
        for record in records:
            model_usage[record.model] = model_usage.get(record.model, 0) + 1

        model_usage_list = [
            {"model": model, "requests": count}
            for model, count in sorted(
                model_usage.items(), key=lambda x: x[1], reverse=True
            )
        ]

        # Error breakdown
        error_records = [r for r in records if r.status != RequestStatus.SUCCESS]
        error_breakdown = {}
        for record in error_records:
            status = record.status.value
            error_breakdown[status] = error_breakdown.get(status, 0) + 1

        error_breakdown_list = [
            {"status": status, "count": count}
            for status, count in sorted(
                error_breakdown.items(), key=lambda x: x[1], reverse=True
            )
        ]

        return DashboardStatsResponse(
            overall_stats=UsageStatsResponse(**overall_stats),
            top_api_keys=top_api_keys,
            hourly_activity=hourly_activity_list,
            model_usage=model_usage_list,
            error_breakdown=error_breakdown_list,
        )

    except Exception as e:
        logger.error(f"Error fetching dashboard stats: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching dashboard stats: {str(e)}"
        )


@router.get("/export/chat-messages")
async def export_chat_messages(
    api_key: Optional[str] = Query(None, description="Filter by API key"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    format: str = Query("json", description="Export format: json or csv"),
    current_user: str = Depends(require_auth),
):
    """Export chat messages data"""
    try:
        # Build filter conditions
        filters = {}
        if api_key:
            filters["api_key"] = api_key
        if start_date:
            filters["timestamp__gte"] = start_date
        if end_date:
            filters["timestamp__lte"] = end_date

        # Get all messages (be careful with large datasets)
        messages = await ChatMessage.get_multi(
            skip=0, limit=10000, order_by="-timestamp", **filters
        )

        if format.lower() == "csv":
            import csv
            import io

            output = io.StringIO()
            writer = csv.writer(output)

            # Write header
            writer.writerow(
                [
                    "ID",
                    "Request ID",
                    "API Key",
                    "Timestamp",
                    "Model",
                    "User Prompt",
                    "Optimized Prompt",
                    "Assistant Response",
                    "Max Tokens",
                    "Temperature",
                    "Stream",
                    "Enable Retrieval",
                    "Collection Name",
                    "IP Address",
                ]
            )

            # Write data
            for msg in messages:
                writer.writerow(
                    [
                        msg.id,
                        msg.request_id,
                        msg.api_key,
                        msg.timestamp,
                        msg.model,
                        msg.user_prompt,
                        msg.optimized_prompt,
                        msg.assistant_response,
                        msg.max_tokens,
                        msg.temperature,
                        msg.stream,
                        msg.enable_retrieval,
                        msg.collection_name,
                        msg.ip_address,
                    ]
                )

            return {"data": output.getvalue(), "format": "csv"}
        else:
            # JSON format
            data = []
            for msg in messages:
                data.append(
                    {
                        "id": msg.id,
                        "request_id": msg.request_id,
                        "api_key": msg.api_key,
                        "timestamp": msg.timestamp.isoformat(),
                        "model": msg.model,
                        "user_prompt": msg.user_prompt,
                        "optimized_prompt": msg.optimized_prompt,
                        "assistant_response": msg.assistant_response,
                        "max_tokens": msg.max_tokens,
                        "temperature": msg.temperature,
                        "stream": msg.stream,
                        "enable_retrieval": msg.enable_retrieval,
                        "collection_name": msg.collection_name,
                        "ip_address": msg.ip_address,
                    }
                )

            return {"data": data, "format": "json", "count": len(data)}

    except Exception as e:
        logger.error(f"Error exporting chat messages: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error exporting chat messages: {str(e)}"
        )


@router.delete("/chat-messages/{request_id}")
async def delete_chat_message(
    request_id: str, current_user: str = Depends(require_auth)
):
    """Delete a chat message by request ID"""
    try:
        message = await ChatMessage.get_or_none(request_id=request_id)
        if not message:
            raise HTTPException(status_code=404, detail="Chat message not found")

        await message.delete_item()
        return {"message": "Chat message deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting chat message: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error deleting chat message: {str(e)}"
        )


@router.delete("/usage-records/{request_id}")
async def delete_usage_record(
    request_id: str, current_user: str = Depends(require_auth)
):
    """Delete a usage record by request ID"""
    try:
        record = await UsageRecord.get_or_none(request_id=request_id)
        if not record:
            raise HTTPException(status_code=404, detail="Usage record not found")

        await record.delete_item()
        return {"message": "Usage record deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting usage record: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error deleting usage record: {str(e)}"
        )
