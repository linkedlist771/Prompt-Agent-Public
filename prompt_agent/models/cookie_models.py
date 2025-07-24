"""
revgrokapi/models/cookie_models.py

This file defines the tortoise based models for the cookie to restore.
"""
from enum import Enum
from typing import Any, Dict

import numpy as np
from loguru import logger
from tortoise import fields

from prompt_agent.models.base import CRUDBase


class CookieType(str, Enum):  # 注意这里继承 str
    PLUS = "plus"
    BASIC = "basic"
    TEST = "test"


class Cookie(CRUDBase):
    cookie = fields.CharField(max_length=4000, unique=True)
    cookie_type = fields.CharEnumField(enum_type=CookieType, max_length=50)
    account = fields.CharField(max_length=254)
    # cookie = await Cookie.create_item(
    #     cookie="your_cookie_string",
    #     cookie_type=CookieType.PLUS,  # 使用枚举值
    #     account="account_name"
    # )
    #
    # # 查询指定类型的 cookie
    # plus_cookies = await Cookie.get_multi(cookie_type=CookieType.PLUS)

    async def to_dict(self) -> Dict[str, Any]:
        """Convert the model instance to a dictionary, similar to pydantic's model_dump."""
        model_dict = {
            "id": self.id,
            "cookie": self.cookie,
            "cookie_type": self.cookie_type.value if self.cookie_type else None,
            "account": self.account,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        return model_dict


class QueryCategory(str, Enum):
    DEFAULT = "DEFAULT"
    REASONING = "REASONING"
    DEEPSEARCH = "DEEPSEARCH"


class CookieQueries(CRUDBase):
    # 关联到Cookie表的外键
    cookie_ref = fields.ForeignKeyField("models.Cookie", related_name="queries")

    # 查询类别
    category = fields.CharEnumField(enum_type=QueryCategory, max_length=50)

    # 查询权重
    queries_weight = fields.IntField(default=0)

    class Meta:
        table = "cookie_queries"
        # 确保cookie和category的组合是唯一的
        unique_together = (("cookie_ref", "category"),)

    @classmethod
    async def get_or_create(
        cls, cookie: Cookie, category: QueryCategory, default_weight: int = 0
    ):
        """获取或创建指定cookie和类别的权重记录"""
        query_record = await cls.get_or_none(cookie_ref=cookie, category=category)
        if not query_record:
            query_record = await cls.create_item(
                cookie_ref=cookie, category=category, queries_weight=default_weight
            )
        return query_record

    @classmethod
    async def update_weight(cls, cookie: Cookie, category: QueryCategory, weight: int):
        """更新指定cookie和类别的权重值"""
        query_record = await cls.get_or_create(cookie, category)
        query_record.queries_weight = weight
        await query_record.save()
        return query_record

    @classmethod
    async def update_weights(cls, cookie: Cookie, weights: Dict[str, int]):
        """同时更新多个类别的权重值

        参数:
            cookie: Cookie对象
            weights: 类别权重字典，如 {"DEFAULT": 80, "REASONING": 50}

        返回:
            更新的CookieQueries记录数量
        """
        updated_count = 0

        # 先检查当前的权重
        current_weights = await cls.get_weights(cookie)

        for category_name, weight in weights.items():
            try:
                category = QueryCategory(category_name)
                await cls.update_weight(cookie, category, weight)
                updated_count += 1
            except ValueError:
                # 如果类别名称无效，跳过
                continue

        # 检查更新后的权重
        updated_weights = await cls.get_weights(cookie)

        return updated_count

    @classmethod
    async def get_weight(cls, cookie: Cookie, category: QueryCategory):
        """获取指定cookie和类别的权重值"""
        query_record = await cls.get_or_none(cookie_ref=cookie, category=category)
        return query_record.queries_weight if query_record else 0

    @classmethod
    async def get_weights(cls, cookie: Cookie):
        """获取指定cookie的所有类别权重值

        返回:
            类别权重字典，如 {"DEFAULT": 80, "REASONING": 50, "DEEPSEARCH": 30}
        """
        query_records = await cls.filter(cookie_ref=cookie)
        result = {record.category: record.queries_weight for record in query_records}
        return result

    @classmethod
    async def get_cookies_by_weight(
        cls,
        category: QueryCategory,
        min_weight: int = 0,
        cookie_type: CookieType = None,
    ):
        """获取指定类别下满足最小权重要求的cookie列表"""
        filters = {"category": category, "queries_weight__gte": min_weight}

        query = cls.filter(**filters)

        if cookie_type:
            # 如果指定了cookie类型，需要联合查询Cookie表
            query = query.filter(cookie_ref__cookie_type=cookie_type)

        # 获取满足条件的CookieQueries记录，并按权重降序排列
        query_records = await query.order_by("-queries_weight").prefetch_related(
            "cookie_ref"
        )

        # 返回关联的Cookie对象列表
        return [record.cookie_ref for record in query_records]

    @classmethod
    async def get_random_weighted_cookie(cls, category: QueryCategory) -> Cookie:
        """根据权重概率随机选择一个cookie

        使用numpy.random.choice基于权重进行概率采样，而不是简单选择权重最高的

        参数:
            category: 查询类别

        返回:
            随机选择的Cookie对象，如果没有符合条件的cookie则返回None
        """

        # 获取指定类别下所有有权重的记录
        query_records = await cls.filter(
            category=category, queries_weight__gt=0  # 确保只选择权重大于0的记录
        ).prefetch_related("cookie_ref")

        if not query_records:
            return None

        # 提取cookie和对应的权重
        cookies = [record.cookie_ref for record in query_records]
        weights = [record.queries_weight for record in query_records]

        # 将权重归一化为概率分布
        weights = np.array(weights, dtype=float)
        weights = weights / weights.sum()

        # 使用numpy的random.choice基于权重进行采样
        selected_index = np.random.choice(len(cookies), p=weights)
        selected_cookie_info = await cookies[selected_index].to_dict()
        logger.debug(f"Selected cookie: \n{selected_cookie_info}")
        logger.debug(f"Selected weight: {weights[selected_index]}")

        return cookies[selected_index]  # Cookie 返回的是这个类型的。
