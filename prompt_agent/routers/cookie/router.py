from datetime import datetime
from typing import Any, Dict, List, Optional, TypeVar

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from pydantic import BaseModel, Field
from revgrokapi.models.cookie_models import (Cookie, CookieQueries, CookieType,
                                             QueryCategory)
from revgrokapi.periodic_checks.clients_limit_checks import \
    __check_grok_clients_limits
from tortoise import Model, fields
from tortoise.expressions import Q


# Pydantic schemas for API request/response models
class CookieBase(BaseModel):
    cookie: str
    cookie_type: CookieType
    account: str


class CookieCreateRequest(CookieBase):
    pass


class CookieUpdateRequest(BaseModel):
    cookie: Optional[str] = None
    cookie_type: Optional[CookieType] = None
    account: Optional[str] = None


class CookieResponse(CookieBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class CookieTotalCountResponse(BaseModel):
    total_count: int
    model_counts: Dict[str, int]


class CookieTypeModelCountResponse(BaseModel):
    cookie_type: str
    total_count: int
    model_counts: Dict[str, int]


class CookieQueryValuesResponse(BaseModel):
    id: int
    account: str
    cookie_type: str
    queries: Dict[str, float]


# FastAPI router for RESTful endpoints
router = APIRouter()


@router.post(
    "/", response_model=List[CookieResponse], status_code=status.HTTP_201_CREATED
)
async def create_cookie(cookie_in: CookieCreateRequest):
    try:
        cookie = await Cookie.create_item(**cookie_in.model_dump())
        return cookie
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not create cookie: {str(e)}",
        )


@router.post(
    "/batch_upload",
    response_model=List[CookieResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_cookie(cookie: str, cookie_type: CookieType, account: str):
    cookie_str = cookie
    cookie_str = cookie_str.strip()
    cookie_strs = cookie_str.split()
    cookies = []
    accounts = []
    types = [cookie_type] * len(cookie_strs)

    for _cookie_str in cookie_strs:
        logger.debug(_cookie_str)
        account, password, raw_cookie = _cookie_str.split("----")
        cookie = f"sso={raw_cookie}"
        cookies.append(cookie)
        accounts.append(account)
    response = []
    for cookie, account, cookie_type in zip(cookies, accounts, types):
        try:
            cookie = await Cookie.create_item(
                cookie=cookie, cookie_type=cookie_type, account=account
            )
            response.append(cookie)
        except Exception as e:
            # raise HTTPException(
            #     status_code=status.HTTP_400_BAD_REQUEST,
            #     detail=f"Could not create cookie: {str(e)}",
            # )
            from traceback import format_exc

            logger.error(f"Error creating cookie: {format_exc()}")
    return response

    # try:
    #     cookie = await Cookie.create_item(**cookie_in.model_dump())
    #     return cookie
    # except Exception as e:
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail=f"Could not create cookie: {str(e)}",
    #     )


@router.get("/all-with-queries", response_model=List[CookieQueryValuesResponse])
async def get_all_cookies_with_queries():
    """
    获取所有cookie及其三个查询类别的权重值
    """
    # 获取所有cookie
    all_cookies = await Cookie.get_multi()
    result = []

    for cookie in all_cookies:
        # 获取该cookie的所有查询类别权重
        query_records = await CookieQueries.filter(cookie_ref=cookie).all()

        # 将查询类别权重转换为字典
        queries = {}
        for category in QueryCategory:
            # 默认值为0
            queries[category.value] = 0

        # 更新实际值
        for record in query_records:
            queries[record.category.value] = record.queries_weight

        # 构建响应对象
        cookie_data = {
            "id": cookie.id,
            "account": cookie.account,
            "cookie_type": cookie.cookie_type.value,
            "queries": queries,
        }

        result.append(cookie_data)

    return result


@router.get("/{cookie_id}", response_model=CookieResponse)
async def get_cookie(cookie_id: int):
    cookie = await Cookie.get_by_id(cookie_id)
    if not cookie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cookie with ID {cookie_id} not found",
        )
    return cookie


@router.get("/", response_model=List[CookieResponse])
async def list_cookies(
    skip: int = 0,
    limit: int = 100,
    cookie_type: Optional[CookieType] = None,
    search: Optional[str] = None,
):
    filters = {}
    if cookie_type:
        filters["cookie_type"] = cookie_type

    if search:
        cookies = await Cookie.search_items(
            search_fields=["cookie", "account"],
            search_term=search,
            skip=skip,
            limit=limit,
        )
    else:
        cookies = await Cookie.get_multi(skip=skip, limit=limit, **filters)

    return cookies


@router.put("/{cookie_id}", response_model=CookieResponse)
async def update_cookie(cookie_id: int, cookie_in: CookieUpdateRequest):
    cookie = await Cookie.get_by_id(cookie_id)
    if not cookie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cookie with ID {cookie_id} not found",
        )

    update_data = {k: v for k, v in cookie_in.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No valid fields to update"
        )

    updated_cookie = await cookie.update_item(**update_data)
    return updated_cookie


@router.delete("/{cookie_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cookie(cookie_id: int):
    deleted = await Cookie.delete_by_id(cookie_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cookie with ID {cookie_id} not found",
        )


@router.get("/stats/refresh")
async def get_refreshed_cookie_stats():
    await __check_grok_clients_limits()
    return {"message": "Cookie stats refreshed"}


@router.get("/stats/total", response_model=CookieTotalCountResponse)
async def get_total_cookie_stats():
    """
    获取所有cookie的总数和各模型的可用量
    """
    # 获取所有cookie的总数
    total_count = await Cookie.get_count()

    # 获取各模型的可用量（剩余查询数的总和）
    model_counts = {}

    for category in QueryCategory:
        # 获取该模型下所有cookie的记录
        all_records = await CookieQueries.filter(category=category).all()

        # 计算该类别下所有cookie的权重总和（剩余查询数）
        total_weight = sum(record.queries_weight for record in all_records)

        model_counts[category.value] = total_weight

    return {"total_count": total_count, "model_counts": model_counts}


@router.get("/stats/by-type", response_model=List[CookieTypeModelCountResponse])
async def get_cookie_stats_by_type():
    """
    获取按cookie类型分组的各模型可用量
    """
    result = []

    # 遍历所有cookie类型
    for cookie_type in CookieType:
        # 获取该类型的cookie总数
        type_count = await Cookie.get_count(cookie_type=cookie_type)

        # 获取该类型下各模型的可用量（剩余查询数的总和）
        model_counts = {}
        for category in QueryCategory:
            # 获取该类型和模型下所有cookie的记录
            all_records = await CookieQueries.filter(
                cookie_ref__cookie_type=cookie_type, category=category
            ).all()

            # 计算该类别下所有cookie的权重总和（剩余查询数）
            total_weight = sum(record.queries_weight for record in all_records)

            model_counts[category.value] = total_weight

        result.append(
            {
                "cookie_type": cookie_type.value,
                "total_count": type_count,
                "model_counts": model_counts,
            }
        )

    return result
