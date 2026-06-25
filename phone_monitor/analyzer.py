"""LLM 分析模块 — 异步调用 LLM API 进行去重、归类、摘要"""

from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any

import httpx

logger = logging.getLogger(__name__)


async def analyze_news(
    results: list[dict[str, Any]],
    api_key: str,
    base_url: str,
    model: str,
) -> str:
    """异步调用 LLM 对搜索结果进行去重、归类、摘要，生成日报

    返回: Markdown 格式的日报内容
    """
    today = date.today().isoformat()

    simplified = [
        {
            "brand": r.get("brand", "未知"),
            "title": r.get("title", ""),
            "content": r.get("content", "")[:500],
            "url": r.get("url", ""),
            "date": r.get("published_date", ""),
        }
        for r in results
    ]

    system_prompt = """你是一个手机新品情报分析助手。你的任务是分析搜索结果，生成一份结构化日报。

处理步骤：
1. **去重** — 同一产品的不同报道只保留一条（合并信息来源）
2. **归类** — 按品牌分组（OPPO / vivo / 华为 / iPhone / 其他）
3. **提取关键信息** — 产品名称、发布时间、核心卖点（一句话）
4. **判断影响** — 这个发布是"新品发布"、"预热曝光"、"价格调整"还是"行业分析"

输出格式（严格 Markdown）：

## 📱 手机新品情报日报（{日期}）

### 🔵 OPPO
- **{产品名}** | {时间} | {核心卖点}
  - 来源: {来源网站} | 影响: {新品发布/预热曝光/价格调整/行业分析}

### 🟢 vivo
...

### 🔴 华为
...

### ⚪ iPhone
...

### 🟡 其他品牌
...

### 📊 今日总结
- 今日最重磅: {一句话}
- 趋势观察: {一句话}

---

规则：
- 如果完全没有有效新品信息，如实报告"今日无新品动态"
- 不要编造信息，只基于搜索结果
- 保持客观，不要主观评价好坏"""

    user_prompt = f"""日期：{today}

以下是搜索到的各品牌手机相关资讯：

```json
{json.dumps(simplified, ensure_ascii=False, indent=2)}
```

请按上述格式生成日报。"""

    logger.info("🤖 正在调用 LLM 分析 %d 条资讯...", len(results))

    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        try:
            resp = await client.post(
                f"{base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 2000,
                },
            )
            resp.raise_for_status()
            data = resp.json()

            content = data["choices"][0]["message"]["content"]
            logger.info("  ✅ LLM 分析完成，生成 %d 字符", len(content))
            return content

        except httpx.HTTPError as e:
            logger.error("  ❌ LLM 调用失败: %s", e)
            return _fallback_summary(results, today)


def _fallback_summary(results: list[dict[str, Any]], today: str) -> str:
    """LLM 调用失败时的降级方案"""
    lines = [f"## 📱 手机新品情报日报（{today}）\n"]
    lines.append("⚠️ *LLM 分析暂不可用，以下是原始搜索结果*\n")

    for r in results:
        brand = r.get("brand", "未知")
        title = r.get("title", "")
        url = r.get("url", "")
        snippet = (r.get("content", "") or "")[:200]
        lines.append(f"- **[{brand}]** {title}")
        if snippet:
            lines.append(f"  > {snippet}")
        if url:
            lines.append(f"  [🔗 原文]({url})")
        lines.append("")

    return "\n".join(lines)
