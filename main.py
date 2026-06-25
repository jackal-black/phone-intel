#!/usr/bin/env python3
"""
Phone Monitor — 手机新品发布情报监控系统

多数据源（Tavily）搜索 → LLM 去重/归类/摘要 → 飞书推送

用法:
    python main.py                    # 正常运行
    DRY_RUN=true python main.py       # 仅打印日报，不推送飞书
    python main.py --help             # 查看帮助
"""

from __future__ import annotations

import argparse
import logging
import sys

from phone_monitor.analyzer import analyze_news
from phone_monitor.config import Config
from phone_monitor.notifier import push_to_feishu
from phone_monitor.searcher import search_all_brands

# ── 日志配置 ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("phone-monitor")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="📱 手机新品发布情报监控系统",
        epilog="示例: DRY_RUN=true python main.py",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅打印结果，不推送飞书",
    )
    args = parser.parse_args()

    # ── 1. 加载配置 ──
    config = Config.from_env()
    if args.dry_run:
        config.dry_run = True

    missing = config.validate()
    if missing:
        logger.error("❌ 缺少必要配置项，请先设置 .env 文件：\n  " + "\n  ".join(missing))
        sys.exit(1)

    logger.info("=" * 50)
    logger.info("📱 Phone Monitor 启动")
    logger.info("   品牌: %s", ", ".join(config.brands))
    logger.info("   LLM: %s @ %s", config.llm_model, config.llm_base_url)
    logger.info("   推送: %s", "❌ 仅打印 (DRY_RUN)" if config.dry_run else "✅ 飞书")
    logger.info("=" * 50)

    # ── 2. 搜索所有品牌 ──
    results = search_all_brands(config.brands, config.tavily_api_key)

    if not results:
        logger.warning("⚠️  未搜索到任何结果")
        _print_and_push("## 📱 手机新品情报日报\n\n今日无相关资讯。", config)
        return

    # ── 3. LLM 分析 ──
    report = analyze_news(results, config.llm_api_key, config.llm_base_url, config.llm_model)

    # ── 4. 输出/推送 ──
    _print_and_push(report, config)

    logger.info("✅ 完成！")


def _print_and_push(report: str, config: Config) -> None:
    """打印日报并（可选）推送到飞书"""
    # 总是打印到控制台
    print("\n" + "─" * 50)
    print(report)
    print("─" * 50 + "\n")

    # 非 dry-run 时推送飞书
    if not config.dry_run:
        success = push_to_feishu(report, config.feishu_webhook_url)
        if not success:
            logger.warning("⚠️  飞书推送失败，日报已打印到上方")


if __name__ == "__main__":
    main()
