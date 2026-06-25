"""飞书推送模块 — 异步发送结构化消息卡片到飞书群机器人"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

import httpx

logger = logging.getLogger(__name__)


async def push_to_feishu(markdown_content: str, webhook_url: str) -> bool:
    """异步推送日报到飞书群机器人

    解析 markdown 按品牌拆分，构建分块卡片。
    """
    if not webhook_url:
        logger.error("❌ 飞书 Webhook URL 未配置")
        return False

    logger.info("📤 正在推送至飞书...")

    try:
        payload = _build_card(markdown_content)

        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            resp = await client.post(webhook_url, json=payload)
            resp.raise_for_status()

            result = resp.json()
            if result.get("code") == 0:
                logger.info("  ✅ 飞书推送成功")
                return True
            else:
                logger.error("  ❌ 飞书返回错误: %s", result.get("msg", "未知错误"))
                return False

    except httpx.HTTPError as e:
        logger.error("  ❌ 飞书推送失败: %s", e)
        return False


# ══════════════════════════════════════════════════
# 以下为纯同步的卡片构建逻辑（CPU 运算，无需 async）
# ══════════════════════════════════════════════════


def _build_card(md: str) -> dict[str, Any]:
    """将 markdown 日报解析为飞书卡片 payload"""
    sections = _parse_sections(md)

    elements: list[dict[str, Any]] = []

    brand_sections = [s for s in sections if s["type"] == "brand"]
    for i, section in enumerate(brand_sections):
        _add_brand_section(elements, section)
        if i < len(brand_sections) - 1:
            elements.append({"tag": "hr"})

    summary_section = next((s for s in sections if s["type"] == "summary"), None)
    if summary_section:
        elements.append({"tag": "hr"})
        _add_summary_section(elements, summary_section)

    elements.append({"tag": "hr"})
    _add_footer(elements, brand_sections)

    today = datetime.now().strftime("%Y-%m-%d")

    return {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"📱 手机新品情报日报 · {today}",
                },
                "template": "wathet",
            },
            "elements": elements,
        },
    }


def _parse_sections(md: str) -> list[dict[str, Any]]:
    """按 ### 标题拆分为段落"""
    lines = md.strip().split("\n")
    sections: list[dict[str, Any]] = []
    current: list[str] = []
    current_type = "text"
    current_title = ""

    brand_keywords = {"OPPO": "🔵", "vivo": "🟢", "华为": "🔴", "iPhone": "⚪", "其他": "🟡"}

    def flush():
        if current:
            sections.append({
                "type": current_type,
                "title": current_title,
                "lines": current[:],
                "content": "\n".join(current),
            })

    for line in lines:
        m = re.match(r"^###\s+(.*)", line)
        if m:
            flush()
            title = m.group(1).strip()
            current = []
            current_title = title
            current_type = (
                "summary" if "总结" in title or "趋势" in title
                else "brand" if any(k in title for k in brand_keywords)
                else "other"
            )
        else:
            current.append(line)
    flush()
    return sections


def _add_brand_section(elements: list[dict[str, Any]], section: dict[str, Any]) -> None:
    """添加品牌区块"""
    elements.append({
        "tag": "markdown",
        "content": f"**{section['title']}**\n" + "\n".join(section["lines"]),
    })


def _add_summary_section(elements: list[dict[str, Any]], section: dict[str, Any]) -> None:
    """添加总结区块"""
    clean = [l for l in section["lines"] if l.strip()]
    elements.append({
        "tag": "markdown",
        "content": f"**{section['title']}**\n" + "\n".join(clean),
    })


def _add_footer(elements: list[dict[str, Any]], brand_sections: list[dict[str, Any]]) -> None:
    """添加底部统计"""
    stats = [
        f"{s['title'].replace('**', '')} {_count_items(s['lines'])}条"
        for s in brand_sections
    ]
    elements.append({
        "tag": "note",
        "elements": [{"tag": "plain_text", "content": f"🤖 Phone Intel · {' | '.join(stats)}"}],
    })


def _count_items(lines: list[str]) -> int:
    """统计产品条目数"""
    return sum(1 for l in lines if l.strip().startswith("- **") or l.strip().startswith("- **"))
