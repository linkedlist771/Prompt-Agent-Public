import json
import time
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Any, Dict, List, Optional
from uuid import uuid4

from prompt_agent.redis_manager.base_redis_manager import BaseRedisManager


class APIKeyManager(BaseRedisManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 每3小时刷新一次使用次数限制
        self.REFRESH_INTERVAL_HOURS = 3
        self.REFRESH_INTERVAL_SECONDS = self.REFRESH_INTERVAL_HOURS * 3600
        # 默认使用次数限制
        self.DEFAULT_USAGE_LIMIT = 100

    async def create_api_key(
        self, expiration_seconds: int, usage_limit: Optional[int] = None
    ) -> str:
        """创建新的API key"""
        api_key = f"sj-{str(uuid4()).replace('-', '')}"

        if usage_limit is None:
            usage_limit = self.DEFAULT_USAGE_LIMIT

        current_timestamp = int(time.time())

        # 存储API key的基本信息
        key_info = {
            "created_at": current_timestamp,
            "expiration_seconds": expiration_seconds,
            "usage_limit": usage_limit,
            "activated": False,  # 懒激活标志
            "activated_at": None,
            "deleted": False,  # 逻辑删除标志
            "deleted_at": None,
        }

        # 存储API key信息
        await self.set_async(f"apikey:{api_key}:info", json.dumps(key_info))

        # 初始化使用次数
        await self.set_async(f"apikey:{api_key}:total_usage", 0)
        await self.set_async(f"apikey:{api_key}:current_period_usage", 0)
        await self.set_async(f"apikey:{api_key}:last_refresh_time", current_timestamp)

        return api_key

    async def activate_api_key(self, api_key: str) -> Dict[str, Any]:
        """激活API key（懒激活）"""
        key_info = await self._get_key_info(api_key)
        if not key_info:
            return {"success": False, "message": "API key不存在"}

        if key_info.get("deleted"):
            return {"success": False, "message": "API key已被删除"}

        if key_info.get("activated"):
            # 检查是否已过期
            activated_at = key_info.get("activated_at")
            expiration_seconds = key_info.get("expiration_seconds")
            if activated_at and int(time.time()) > activated_at + expiration_seconds:
                return {"success": False, "message": "API key已过期"}
            return {
                "success": True,
                "message": "API key已激活",
                "expires_at": (activated_at or 0) + (expiration_seconds or 0),
            }

        # 激活API key
        current_timestamp = int(time.time())
        key_info["activated"] = True
        key_info["activated_at"] = current_timestamp

        await self.set_async(f"apikey:{api_key}:info", json.dumps(key_info))

        expires_at = current_timestamp + key_info["expiration_seconds"]
        return {
            "success": True,
            "message": "API key激活成功",
            "activated_at": current_timestamp,
            "expires_at": expires_at,
        }

    async def is_api_key_valid(self, api_key: str) -> bool:
        """检查API key是否有效"""
        key_info = await self._get_key_info(api_key)
        if not key_info or key_info.get("deleted"):
            return False

        if not key_info.get("activated"):
            return True  # 未激活但存在的key是有效的

        # 检查是否过期
        activated_at = key_info.get("activated_at")
        expiration_seconds = key_info.get("expiration_seconds")
        if activated_at and int(time.time()) > activated_at + expiration_seconds:
            return False

        return True

    async def increment_usage(self, api_key: str) -> Dict[str, Any]:
        """增加使用次数"""
        # 首先激活API key（如果未激活）
        activation_result = await self.activate_api_key(api_key)
        if not activation_result["success"]:
            return activation_result

        # 检查使用次数限制
        limit_check = await self._check_usage_limit(api_key)
        if not limit_check["can_use"]:
            return {
                "success": False,
                "message": f"使用次数已达限制，请等待重置。{limit_check.get('message', '')}",
            }

        # 增加使用次数
        await self._increment_usage_counters(api_key)

        usage_info = await self.get_usage_info(api_key)
        return {"success": True, "message": "使用次数已更新", "usage_info": usage_info}

    async def get_usage_info(self, api_key: str) -> Dict[str, Any]:
        """获取使用信息"""
        key_info = await self._get_key_info(api_key)
        if not key_info:
            return {}

        total_usage = int(await self.decoded_get(f"apikey:{api_key}:total_usage") or 0)
        current_period_usage = int(
            await self.decoded_get(f"apikey:{api_key}:current_period_usage") or 0
        )
        last_refresh_time = int(
            await self.decoded_get(f"apikey:{api_key}:last_refresh_time") or 0
        )

        # 计算下次重置时间
        next_reset_time = last_refresh_time + self.REFRESH_INTERVAL_SECONDS

        return {
            "total_usage": total_usage,
            "current_period_usage": current_period_usage,
            "usage_limit": key_info.get("usage_limit"),
            "last_refresh_time": last_refresh_time,
            "next_reset_time": next_reset_time,
            "time_until_reset": max(0, next_reset_time - int(time.time())),
        }

    async def get_api_key_info(self, api_key: str) -> Dict[str, Any]:
        """获取API key的完整信息"""
        key_info = await self._get_key_info(api_key)
        if not key_info:
            return {}

        usage_info = await self.get_usage_info(api_key)

        result = {**key_info, **usage_info}

        # 添加状态信息
        if key_info.get("deleted"):
            result["status"] = "deleted"
        elif not key_info.get("activated"):
            result["status"] = "inactive"
        elif key_info.get("activated_at") and int(time.time()) > key_info.get(
            "activated_at", 0
        ) + key_info.get("expiration_seconds", 0):
            result["status"] = "expired"
        else:
            result["status"] = "active"

        return result

    async def update_api_key(self, api_key: str, **kwargs) -> Dict[str, Any]:
        """更新API key信息"""
        key_info = await self._get_key_info(api_key)
        if not key_info:
            return {"success": False, "message": "API key不存在"}

        if key_info.get("deleted"):
            return {"success": False, "message": "API key已被删除"}

        # 允许更新的字段
        allowed_fields = ["expiration_seconds", "usage_limit"]
        updated = False

        for field, value in kwargs.items():
            if field in allowed_fields:
                key_info[field] = value
                updated = True

        if updated:
            await self.set_async(f"apikey:{api_key}:info", json.dumps(key_info))
            return {"success": True, "message": "API key更新成功"}
        else:
            return {"success": False, "message": "没有有效的更新字段"}

    async def delete_api_key(self, api_key: str) -> Dict[str, Any]:
        """逻辑删除API key"""
        key_info = await self._get_key_info(api_key)
        if not key_info:
            return {"success": False, "message": "API key不存在"}

        if key_info.get("deleted"):
            return {"success": False, "message": "API key已被删除"}

        # 逻辑删除
        key_info["deleted"] = True
        key_info["deleted_at"] = int(time.time())

        await self.set_async(f"apikey:{api_key}:info", json.dumps(key_info))

        return {"success": True, "message": "API key删除成功"}

    async def list_api_keys(
        self, include_deleted: bool = False
    ) -> List[Dict[str, Any]]:
        """列出所有API keys"""
        redis_client = await self.get_aioredis()
        keys = await redis_client.keys("apikey:*:info")

        result = []
        for key in keys:
            api_key = key.split(":")[1]
            key_info = await self.get_api_key_info(api_key)

            if key_info and (include_deleted or not key_info.get("deleted")):
                key_info["api_key"] = api_key
                result.append(key_info)

        return result

    async def _get_key_info(self, api_key: str) -> Optional[Dict[str, Any]]:
        """获取API key的基本信息"""
        info_str = await self.decoded_get(f"apikey:{api_key}:info")
        if not info_str:
            return None

        try:
            return json.loads(info_str)
        except json.JSONDecodeError:
            return None

    async def _check_usage_limit(self, api_key: str) -> Dict[str, Any]:
        """检查使用次数限制"""
        key_info = await self._get_key_info(api_key)
        if not key_info:
            return {"can_use": False, "message": "API key不存在"}

        current_timestamp = int(time.time())
        last_refresh_time = int(
            await self.decoded_get(f"apikey:{api_key}:last_refresh_time") or 0
        )

        # 检查是否需要重置计数器
        if current_timestamp >= last_refresh_time + self.REFRESH_INTERVAL_SECONDS:
            await self._reset_period_usage(api_key, current_timestamp)
            return {"can_use": True, "message": "使用次数已重置"}

        # 检查当前周期使用次数
        current_period_usage = int(
            await self.decoded_get(f"apikey:{api_key}:current_period_usage") or 0
        )
        usage_limit = key_info.get("usage_limit", self.DEFAULT_USAGE_LIMIT)

        if current_period_usage >= usage_limit:
            next_reset_time = last_refresh_time + self.REFRESH_INTERVAL_SECONDS
            time_until_reset = next_reset_time - current_timestamp
            reset_time_str = datetime.fromtimestamp(next_reset_time).strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            return {
                "can_use": False,
                "message": f"使用次数已达限制({current_period_usage}/{usage_limit})，将在 {reset_time_str} 重置",
            }

        return {"can_use": True}

    async def _increment_usage_counters(self, api_key: str):
        """增加使用计数器"""
        redis_client = await self.get_aioredis()
        await redis_client.incr(f"apikey:{api_key}:total_usage")
        await redis_client.incr(f"apikey:{api_key}:current_period_usage")

    async def _reset_period_usage(self, api_key: str, timestamp: int):
        """重置周期使用次数"""
        await self.set_async(f"apikey:{api_key}:current_period_usage", 0)
        await self.set_async(f"apikey:{api_key}:last_refresh_time", timestamp)


@lru_cache()
def get_api_key_manager():
    return APIKeyManager()
