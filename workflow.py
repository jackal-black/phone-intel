"""
Prefect Workflow 定义 — 手机新品情报日报

工作流 DAG:

    ┌─ search_oppo ─┐
    ├─ search_vivo  ├→ flatten → analyze → notify
    ├─ search_华为   │
    └─ search_iPhone┘

特性:
    - ✅ 并行搜索: 4个品牌同时搜索 (task.submit)
    - ✅ 自动重试: 网络失败自动重试2次
    - ✅ 超时控制: 每个 task 都有超时保护
    - ✅ 条件分支: 无结果时跳过 LLM 分析
    - ✅ 定时调度: Flow.serve(cron="0 9 * * *") 每日自动运行
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from prefect import flow, task

from phone_monitor.analyzer import analyze_news
from phone_monitor.config import Config
from phone_monitor.notifier import push_to_feishu
from phone_monitor.searcher import search_brand

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════
# Task 层 — 每个步骤都是独立可编排的工作单元
# ══════════════════════════════════════════════════


@task(
    retries=2,
    retry_delay_seconds=10,
    timeout_seconds=30,
    tags=["search", "tavily"],
)
def task_search_brand(brand: str, api_key: str) -> list[dict[str, Any]]:
    """[Task] 搜索单个品牌 — API 失败时自动重试 2 次"""
    return search_brand(brand, api_key)


@task(tags=["transform"])
def task_flatten_results(
    results_by_brand: list[list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """[Task] 合并所有品牌的搜索结果，按相关性排序"""
    all_results: list[dict[str, Any]] = []
    for brand_results in results_by_brand:
        all_results.extend(brand_results)
    all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
    logger.info("📦 合并完成，共 %d 条结果", len(all_results))
    return all_results


@task(
    retries=1,
    retry_delay_seconds=10,
    timeout_seconds=90,
    tags=["llm", "analyze"],
)
def task_analyze(
    results: list[dict[str, Any]],
    api_key: str,
    base_url: str,
    model: str,
) -> str:
    """[Task] LLM 分析 — 空结果快速返回，不浪费 LLM 调用"""
    if not results:
        logger.info("⏭️  无搜索结果，跳过 LLM 分析")
        return "## 📱 手机新品情报日报\n\n今日无相关资讯。"
    return analyze_news(results, api_key, base_url, model)


@task(tags=["notify", "feishu"])
def task_notify(report: str, webhook_url: str, dry_run: bool = False) -> bool:
    """[Task] 推送或打印日报"""
    if dry_run:
        print("\n" + "─" * 50)
        print(report)
        print("─" * 50 + "\n")
        return True
    return push_to_feishu(report, webhook_url)


# ══════════════════════════════════════════════════
# Flow 层 — 工作流编排，展示 DAG 结构
# ══════════════════════════════════════════════════


@flow(
    name="📱 Phone Intel 日报",
    description="手机竞品情报日报工作流：并行搜索 → LLM 分析 → 飞书推送",
    log_prints=True,
)
def daily_report_flow(config: Config | None = None) -> str:
    """手机新品情报日报工作流

    Steps:
        1. 并行搜索所有品牌（task.submit → 4 个并发）
        2. 合并搜索结果
        3. LLM 去重 / 归类 / 摘要
        4. 飞书卡片推送
    """
    if config is None:
        config = Config.from_env()

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"{'=' * 50}")
    print(f"📱 Phone Intel 日报工作流 — {now}")
    print(f"   品牌: {', '.join(config.brands)}")
    print(f"   LLM:  {config.llm_model} @ {config.llm_base_url}")
    print(f"   推送: {'DRY_RUN' if config.dry_run else '飞书'}")
    print(f"{'=' * 50}")

    # ── Step 1: 并行搜索 ──────────────────────────
    print("🔍 [1/4] 并行搜索所有品牌...")
    futures = {}
    for brand in config.brands:
        # task.submit() → 异步执行，不阻塞
        futures[brand] = task_search_brand.submit(brand, config.tavily_api_key)

    # 收集各品牌的搜索结果
    results_by_brand = [futures[b].result() for b in config.brands]

    # ── Step 2: 合并 ──────────────────────────────
    print("📦 [2/4] 合并搜索结果...")
    all_results = task_flatten_results(results_by_brand)

    # ── Step 3: LLM 分析 ──────────────────────────
    print("🤖 [3/4] LLM 去重归类摘要...")
    report = task_analyze(
        all_results,
        config.llm_api_key,
        config.llm_base_url,
        config.llm_model,
    )

    # ── Step 4: 推送 ──────────────────────────────
    action = "打印（DRY_RUN）" if config.dry_run else "推送飞书"
    print(f"📤 [4/4] {action}...")
    success = task_notify(report, config.feishu_webhook_url, config.dry_run)

    # ── 完成 ──
    status = "✅ 完成" if success else "❌ 推送失败"
    print(f"{status} — 日报共 {len(report)} 字符")
    return report
