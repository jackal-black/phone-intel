"""搜索模块 — 调用 Tavily Search API 获取品牌最新资讯"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import requests

logger = logging.getLogger(__name__)

# Tavily API 端点
TAVILY_SEARCH_URL = "https://api.tavily.com/search"


def search_brand(brand: str, api_key: str, max_results: int = 5) -> list[dict[str, Any]]:
    """搜索单个品牌的最新发布资讯

    参数:
        brand: 品牌名称（如 "OPPO", "iPhone"）
        api_key: Tavily API Key
        max_results: 每个品牌返回的结果数

    返回:
        [{"title", "url", "content", "published_date", "score"}, ...]
    """
    query = f"{brand} 最新手机 发布 动态"

    logger.info("🔍 正在搜索: %s", query)

    try:
        resp = requests.post(
            TAVILY_SEARCH_URL,
            json={
                "api_key": api_key,
                "query": query,
                "search_depth": "basic",        # "basic" 更快，"advanced" 更深入
                "max_results": max_results,
                "include_domains": [],           # 不限来源
                "exclude_domains": [],           # 不排除
                "include_answer": False,         # 不需要 summary answer
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        results = data.get("results", [])
        for r in results:
            r["brand"] = brand  # 标记品牌来源

        logger.info("  ✅ 获取到 %d 条结果", len(results))
        return results

    except requests.RequestException as e:
        logger.error("  ❌ 搜索失败: %s", e)
        return []


def search_all_brands(brands: list[str], api_key: str) -> list[dict[str, Any]]:
    """搜索所有品牌，返回合并结果"""
    all_results: list[dict[str, Any]] = []

    for brand in brands:
        results = search_brand(brand, api_key)
        all_results.extend(results)

    # 按相关性得分降序排列
    all_results.sort(key=lambda x: x.get("score", 0), reverse=True)

    logger.info("📦 总共获取到 %d 条结果", len(all_results))
    return all_results
