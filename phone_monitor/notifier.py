"""飞书推送模块 — 发送结构化消息卡片到飞书群机器人"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

import requests

logger = logging.getLogger(__name__)


def push_to_feishu(markdown_content: str, webhook_url: str) -> bool:
    """将 LLM 日报内容转为精美的飞书卡片并推送

    解析 markdown 按品牌拆分，每个品牌独立展示，视觉层次清晰。
    """
    if not webhook_url:
        logger.error("❌ 飞书 Webhook URL 未配置")
        return False

    logger.info("📤 正在推送至飞书...")

    try:
        payload = _build_card(markdown_content)
        resp = requests.post(webhook_url, json=payload, timeout=10)
        resp.raise_for_status()

        result = resp.json()
        if result.get("code") == 0:
            logger.info("  ✅ 飞书推送成功")
            return True
        else:
            logger.error("  ❌ 飞书返回错误: %s", result.get("msg", "未知错误"))
            return False

    except requests.RequestException as e:
        logger.error("  ❌ 飞书推送失败: %s", e)
        return False


# ── 卡片构建 ──


def _build_card(md: str) -> dict[str, Any]:
    """将 markdown 日报解析为飞书卡片 payload"""
    sections = _parse_sections(md)

    elements: list[dict[str, Any]] = []

    # ── 品牌区块 ──
    brand_sections = [s for s in sections if s["type"] == "brand"]
    for i, section in enumerate(brand_sections):
        _add_brand_section(elements, section)
        # 品牌之间加分割线
        if i < len(brand_sections) - 1:
            elements.append({"tag": "hr"})

    # ── 总结区块（如果有） ──
    summary_section = next((s for s in sections if s["type"] == "summary"), None)
    if summary_section:
        elements.append({"tag": "hr"})
        _add_summary_section(elements, summary_section)

    # ── 品牌摘要脚注（一行列出所有品牌 + 数量） ──
    elements.append({"tag": "hr"})
    _add_footer(elements, brand_sections)

    # 日期
    today = datetime.now().strftime("%Y-%m-%d")

    return {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"📱 手机新品情报日报 · {today}",
                },
                "template": "wathet",  # 浅蓝色系
            },
            "elements": elements,
        },
    }


# ── 解析 ──


def _parse_sections(md: str) -> list[dict[str, Any]]:
    """将 markdown 按 ### 标题拆分为段落，标记类型"""
    lines = md.strip().split("\n")
    sections: list[dict[str, Any]] = []
    current: list[str] = []
    current_type = "text"
    current_title = ""

    brand_keywords = {
        "OPPO": "🔵",
        "vivo": "🟢",
        "华为": "🔴",
        "iPhone": "⚪",
        "其他": "🟡",
    }

    def flush():
        if current:
            sections.append({
                "type": current_type,
                "title": current_title,
                "lines": current[:],
                "content": "\n".join(current),
            })

    for line in lines:
        # 检测 ### 标题行
        m = re.match(r"^###\s+(.*)", line)
        if m:
            flush()
            title = m.group(1).strip()
            current = []
            current_title = title
            # 判断段落类型
            if "总结" in title or "趋势" in title:
                current_type = "summary"
            elif any(k in title for k in brand_keywords):
                current_type = "brand"
            else:
                current_type = "other"
        else:
            current.append(line)
    flush()
    return sections


# ── 品牌区块 ──


def _add_brand_section(elements: list[dict[str, Any]], section: dict[str, Any]) -> None:
    """添加一个品牌的产品列表区块"""
    title = section["title"]
    lines = section["lines"]

    # 品牌标题行（带 emoji + 品牌名）
    content_parts = [f"**{title}**"]
    content_parts.extend(lines)

    elements.append({
        "tag": "markdown",
        "content": "\n".join(content_parts),
    })


# ── 总结区块 ──


def _add_summary_section(elements: list[dict[str, Any]], section: dict[str, Any]) -> None:
    """添加今日总结区块（使用不同色系）"""
    lines = section["lines"]
    # 清理空行
    clean = [l for l in lines if l.strip()]

    # 总结标题
    parts = [f"**{section['title']}**"]
    parts.extend(clean)

    elements.append({
        "tag": "markdown",
        "content": "\n".join(parts),
    })


# ── 脚注 ──


def _add_footer(elements: list[dict[str, Any]], brand_sections: list[dict[str, Any]]) -> None:
    """添加底部统计脚注"""
    stats = []
    for s in brand_sections:
        title = s["title"]
        count = _count_items(s["lines"])
        stats.append(f"{title.replace('**', '')} {count}条")

    stats_str = " | ".join(stats)

    elements.append({
        "tag": "note",
        "elements": [
            {"tag": "plain_text", "content": f"🤖 Phone Monitor · {stats_str}"},
        ],
    })


def _count_items(lines: list[str]) -> int:
    """统计某个品牌段落中的产品条目数"""
    count = 0
    for line in lines:
        if line.strip().startswith("- **") or re.match(r"^\s*-\s*\*\*", line):
            count += 1
    return count or len([l for l in lines if l.strip().startswith("-")])
