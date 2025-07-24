import asyncio
from functools import lru_cache
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
# from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import BaseModel, Field

from prompt_agent.redis_manager.api_key_manager import APIKeyManager

router = APIRouter()


# Pydantic models for request/response
class CreateAPIKeyRequest(BaseModel):
    days: Optional[int] = Field(default=30, description="过期天数")
    hours: Optional[int] = Field(default=0, description="过期小时数")
    minutes: Optional[int] = Field(default=0, description="过期分钟数")
    seconds: Optional[int] = Field(default=0, description="过期秒数")
    usage_limit: Optional[int] = Field(default=100, description="使用次数限制")
    numbers: int = Field(default=1, description="要创建的API key数量")


class UpdateAPIKeyRequest(BaseModel):
    expiration_seconds: Optional[int] = Field(default=None, description="过期秒数")
    usage_limit: Optional[int] = Field(default=None, description="使用次数限制")


class BatchAPIKeysDeleteRequest(BaseModel):
    api_keys: List[str] = Field(description="要删除的API key列表")


# Dependency
@lru_cache()
def get_api_key_manager():
    return APIKeyManager()


def calculate_expiration_seconds(
    days: int = 30, hours: int = 0, minutes: int = 0, seconds: int = 0
) -> int:
    """计算总的过期秒数"""
    total_seconds = (days * 24 * 60 * 60) + (hours * 60 * 60) + (minutes * 60) + seconds
    return total_seconds


@router.post("/create_key")
async def create_key(
    create_request: CreateAPIKeyRequest,
    manager: APIKeyManager = Depends(get_api_key_manager),
):
    """创建API key"""
    try:
        expiration_seconds = calculate_expiration_seconds(
            days=create_request.days or 30,
            hours=create_request.hours or 0,
            minutes=create_request.minutes or 0,
            seconds=create_request.seconds or 0,
        )
        api_key_number = create_request.numbers
        tasks = []
        for _ in range(api_key_number):
            task = asyncio.create_task(
                manager.create_api_key(
                    expiration_seconds=expiration_seconds,
                    usage_limit=create_request.usage_limit,
                )
            )
            tasks.append(task)
        api_keys = await asyncio.gather(*tasks)
        # api_key = await manager.create_api_key(
        #     expiration_seconds=expiration_seconds,
        #     usage_limit=create_request.usage_limit,
        # )

        return {
            "success": True,
            "api_keys": api_keys,
            "expiration_seconds": expiration_seconds,
        }
    except Exception as e:
        logger.error(f"创建API key失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建API key失败: {str(e)}")


@router.post("/activate_key/{api_key}")
async def activate_key(
    api_key: str, manager: APIKeyManager = Depends(get_api_key_manager)
):
    """激活API key"""
    try:
        result = await manager.activate_api_key(api_key)
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=400, detail=result["message"])
    except Exception as e:
        logger.error(f"激活API key失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"激活API key失败: {str(e)}")


@router.get("/validate_key/{api_key}")
async def validate_key(
    api_key: str, manager: APIKeyManager = Depends(get_api_key_manager)
):
    """验证API key是否有效"""
    try:
        is_valid = await manager.is_api_key_valid(api_key)
        return {"api_key": api_key, "is_valid": is_valid}
    except Exception as e:
        logger.error(f"验证API key失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"验证API key失败: {str(e)}")


@router.post("/increment_usage/{api_key}")
async def increment_usage(
    api_key: str, manager: APIKeyManager = Depends(get_api_key_manager)
):
    """增加API key使用次数"""
    try:
        result = await manager.increment_usage(api_key)
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=400, detail=result["message"])
    except Exception as e:
        logger.error(f"增加使用次数失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"增加使用次数失败: {str(e)}")


@router.get("/usage_info/{api_key}")
async def get_usage_info(
    api_key: str, manager: APIKeyManager = Depends(get_api_key_manager)
):
    """获取API key使用信息"""
    try:
        usage_info = await manager.get_usage_info(api_key)
        if not usage_info:
            raise HTTPException(status_code=404, detail="API key不存在")
        return {"api_key": api_key, "usage_info": usage_info}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取使用信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取使用信息失败: {str(e)}")


@router.get("/get_information/{api_key}")
async def get_information(
    api_key: str, manager: APIKeyManager = Depends(get_api_key_manager)
):
    """获取API key完整信息"""
    try:
        key_info = await manager.get_api_key_info(api_key)
        if not key_info:
            raise HTTPException(status_code=404, detail="API key不存在")
        return {"api_key": api_key, "information": key_info}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取API key信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取API key信息失败: {str(e)}")


@router.put("/update_key/{api_key}")
async def update_key(
    api_key: str,
    update_request: UpdateAPIKeyRequest,
    manager: APIKeyManager = Depends(get_api_key_manager),
):
    """更新API key信息"""
    try:
        update_data = {}
        if update_request.expiration_seconds is not None:
            update_data["expiration_seconds"] = update_request.expiration_seconds
        if update_request.usage_limit is not None:
            update_data["usage_limit"] = update_request.usage_limit

        if not update_data:
            raise HTTPException(status_code=400, detail="没有提供要更新的字段")

        result = await manager.update_api_key(api_key, **update_data)
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=400, detail=result["message"])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新API key失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新API key失败: {str(e)}")


@router.delete("/delete_key/{api_key}")
async def delete_key(
    api_key: str, manager: APIKeyManager = Depends(get_api_key_manager)
):
    """删除API key"""
    try:
        result = await manager.delete_api_key(api_key)
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=400, detail=result["message"])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除API key失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除API key失败: {str(e)}")


@router.delete("/delete_batch_keys")
async def delete_batch_keys(
    batch_request: BatchAPIKeysDeleteRequest,
    manager: APIKeyManager = Depends(get_api_key_manager),
):
    """批量删除API keys"""
    try:
        results = []
        for api_key in batch_request.api_keys:
            result = await manager.delete_api_key(api_key)
            results.append({"api_key": api_key, "result": result})

        return {"batch_delete_results": results}
    except Exception as e:
        logger.error(f"批量删除API keys失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"批量删除API keys失败: {str(e)}")


@router.get("/list_keys")
async def list_keys(
    include_deleted: bool = False, manager: APIKeyManager = Depends(get_api_key_manager)
):
    """列出所有API keys"""
    try:
        api_keys = await manager.list_api_keys(include_deleted=include_deleted)
        return {"api_keys": api_keys, "count": len(api_keys)}
    except Exception as e:
        logger.error(f"列出API keys失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"列出API keys失败: {str(e)}")
