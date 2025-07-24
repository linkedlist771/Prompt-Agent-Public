# base.py
from typing import Any, Dict, List, Optional, TypeVar

from pydantic import BaseModel
from tortoise import Model, fields
from tortoise.expressions import Q

ModelType = TypeVar("ModelType", bound=Model)


class CRUDBase(Model):
    id = fields.IntField(pk=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        abstract = True

    @classmethod
    async def create_item(cls, **kwargs) -> ModelType:
        """创建一条记录"""
        return await cls.create(**kwargs)

    @classmethod
    async def get_by_id(cls, id: int) -> Optional[ModelType]:
        """通过id获取记录"""
        return await cls.get_or_none(id=id)

    @classmethod
    async def get_multi(
        cls, *, skip: int = 0, limit: int = 100, order_by: str = "-id", **filters
    ) -> List[ModelType]:
        """获取多条记录"""
        query = cls.filter(**filters)
        if order_by:
            query = query.order_by(order_by)
        return await query.offset(skip).limit(limit)

    @classmethod
    async def get_count(cls, **filters) -> int:
        """获取记录总数"""
        return await cls.filter(**filters).count()

    async def update_item(self, **kwargs) -> ModelType:
        """更新记录"""
        for key, value in kwargs.items():
            setattr(self, key, value)
        await self.save()
        return self

    @classmethod
    async def update_by_id(cls, id: int, **kwargs) -> Optional[ModelType]:
        """通过id更新记录"""
        obj = await cls.get_or_none(id=id)
        if obj:
            for key, value in kwargs.items():
                setattr(obj, key, value)
            await obj.save()
            return obj
        return None

    async def delete_item(self) -> bool:
        """删除记录"""
        await self.delete()
        return True

    @classmethod
    async def delete_by_id(cls, id: int) -> bool:
        """通过id删除记录"""
        obj = await cls.get_or_none(id=id)
        if obj:
            await obj.delete()
            return True
        return False

    @classmethod
    async def search_items(
        cls,
        search_fields: List[str],
        search_term: str,
        skip: int = 0,
        limit: int = 100,
        order_by: str = "-id",
    ) -> List[ModelType]:
        """搜索记录"""
        if not search_term or not search_fields:
            return await cls.get_multi(skip=skip, limit=limit, order_by=order_by)

        q_filters = Q()
        for field in search_fields:
            q_filters |= Q(**{f"{field}__icontains": search_term})

        query = cls.filter(q_filters)
        if order_by:
            query = query.order_by(order_by)
        return await query.offset(skip).limit(limit)

    class PydanticMeta:
        exclude = ["created_at", "updated_at"]


if __name__ == "__main__":
    # usage cases

    from tortoise import fields

    from .base import CRUDBase

    class User(CRUDBase):
        username = fields.CharField(max_length=50, unique=True)
        email = fields.CharField(max_length=100)
        is_active = fields.BooleanField(default=True)

        class Meta:
            table = "users"

    # 使用示例
    async def example():
        # 创建用户
        user = await User.create_item(username="test_user", email="test@example.com")

        # 获取用户
        user = await User.get_by_id(1)

        # 更新用户
        user = await user.update_item(email="new@example.com")

        # 获取用户列表
        users = await User.get_multi(
            skip=0, limit=10, order_by="-created_at", is_active=True
        )

        # 搜索用户
        users = await User.search_items(
            search_fields=["username", "email"], search_term="test", limit=10
        )

        # 删除用户
        await user.delete_item()
