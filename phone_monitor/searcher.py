"""搜索模块 — 异步调用 Tavily Search API 获取品牌最新资讯"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import httpx

logger = logging.getLogger(__name__)

TAVILY_SEARCH_URL = "https://api.tavily.com/search"


async def search_brand(
    brand: str, api_key: str, max_results: int = 5
) -> list[dict[str, Any]]:
    """异步搜索单个品牌的最新发布资讯

    使用 httpx.AsyncClient 实现非阻塞 IO，
    支持 Prefect async task 的可中断超时。
    """
    query = f"{brand} 最新手机 发布 动态"
    logger.info("🔍 正在搜索: %s", query)

    async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
        try:
            resp = await client.post(
                TAVILY_SEARCH_URL,
                json={
                    "api_key": api_key,
                    "query": query,
                    "search_depth": "basic",
                    "max_results": max_results,
                    "include_domains": [],
                    "exclude_domains": [],
                    "include_answer": False,
                },
            )
            resp.raise_for_status()
            data = resp.json()

            results = data.get("results", [])
            for r in results:
                r["brand"] = brand

            logger.info("  ✅ 获取到 %d 条结果", len(results))
            return results

        except httpx.HTTPError as e:
            logger.error("  ❌ 搜索失败: %s", e)
            return []


# 保留同步版本给不需要 async 的调用方
def search_brand_sync(brand: str, api_key: str, max_results: int = 5) -> list[dict[str, Any]]:
    """同步包装 — 用于非 workflow 场景"""
    import asyncio
    return asyncio.run(search_brand(brand, api_key, max_results))
