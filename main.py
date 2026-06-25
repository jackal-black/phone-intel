#!/usr/bin/env python3
"""
📱 Phone Intel — 手机新品发布情报监控系统 (Async Prefect Workflow)

异步工作流引擎：
  并行搜索 → LLM 分析 → 飞书推送
  全程 httpx.AsyncClient 非阻塞 IO

用法:
    python main.py                      # 运行一次工作流
    python main.py --dry-run            # 测试模式（仅打印）
    python main.py --schedule           # 启动定时调度（每天 09:00）
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from phone_monitor.config import Config
from workflow import daily_report_flow


def main() -> None:
    parser = argparse.ArgumentParser(
        description="📱 Phone Intel — 手机竞品情报日报 Workflow",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅打印结果，不推送飞书",
    )
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="启动 Prefect 定时调度（每天 09:00），保持进程常驻",
    )
    args = parser.parse_args()

    config = Config.from_env()
    if args.dry_run:
        config.dry_run = True

    missing = config.validate()
    if missing:
        print("❌ 缺少必要配置项，请先设置 .env 文件：")
        for item in missing:
            print(f"   - {item}")
        sys.exit(1)

    if args.schedule:
        print("⏰ 启动定时调度（每天 09:00）...")
        print("   按 Ctrl+C 停止\n")
        daily_report_flow.serve(
            name="phone-intel-daily",
            cron="0 9 * * *",
            tags=["phone-intel", "daily-report"],
        )
    else:
        # async flow 需要在事件循环中执行
        asyncio.run(daily_report_flow(config))


if __name__ == "__main__":
    main()
