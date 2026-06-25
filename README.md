# 📱 Phone Intel — 手机竞品情报日报 Workflow

> **Prefect 工作流引擎 + Tavily 搜索 + DeepSeek LLM + 飞书推送**
> 
> 不只是一个脚本——这是一个完整的 **DAG 工作流**项目，展示任务编排、并行调度、自动重试、条件分支等 workflow 核心概念。

---

## 工作流 DAG

```
                         ┌─ task_search_brand("OPPO") ─┐
                         ├─ task_search_brand("vivo")  ├─┐
  Flow 启动 ─→ 并行搜索 ──┼─ task_search_brand("华为")  ├─→ task_flatten_results
                         └─ task_search_brand("iPhone")┘─┘
                                                              │
                                                              ↓
                                                   task_analyze (LLM 去重/归类/摘要)
                                                              │
                                                              ↓
                                                   task_notify (飞书推送 / 打印)
```

### 工作流特性

| 特性 | 实现方式 | 代码位置 |
|------|----------|----------|
| **DAG 编排** | Prefect `@flow` 定义有向无环图 | `workflow.py:122` |
| **并行任务** | `task.submit()` 异步提交，4品牌同时搜索 | `workflow.py:136-139` |
| **自动重试** | `@task(retries=2, retry_delay_seconds=10)` | `workflow.py:35` |
| **超时控制** | `@task(timeout_seconds=30)` 防止 API 卡死 | `workflow.py:36` |
| **条件分支** | 无结果时跳过 LLM 调用，节省 tokens | `workflow.py:86-89` |
| **定时调度** | `Flow.serve(cron="0 9 * * *")` 每日自动运行 | `main.py:53` |
| **任务追踪** | Prefect Server 可视化查看每次运行状态 | 启动后访问 `http://localhost:8268` |

---

## 快速开始

### 1. 安装

```bash
pip install -r requirements.txt
```

### 2. 配置

```bash
cp .env.example .env
# 填入 TAVILY_API_KEY, LLM_API_KEY, FEISHU_WEBHOOK_URL
```

### 3. 运行

```bash
# 运行一次工作流
python main.py

# 测试模式（仅打印，不推送）
python main.py --dry-run

# 启动定时调度（每天 09:00 自动运行）
python main.py --schedule
```

### 4. 查看工作流状态

运行 `python main.py` 时 Prefect 会自动启动一个临时 Web UI：

```
http://localhost:8268
```

可以查看：
- 每次 Flow Run 的执行状态 ✅ / ❌
- 每个 Task 的耗时、重试次数、输入输出
- 整个 DAG 的可视化图谱

---

## 项目结构

```
phone-intel/
├── workflow.py              # 📌 Prefect 工作流定义 (@flow + @task)
├── main.py                  # 入口：运行工作流 / 启动定时调度
├── phone_monitor/
│   ├── searcher.py          # Tavily 搜索（被 task 封装）
│   ├── analyzer.py          # LLM 分析（被 task 封装）
│   ├── notifier.py          # 飞书推送（被 task 封装）
│   └── config.py            # 配置管理
├── requirements.txt         # prefect + requests
├── .env.example             # 配置模板
├── .gitignore
├── setup.sh                 # 一键部署脚本
└── README.md
```

---

## 简历价值

### 技术栈关键词

`Prefect` · `Workflow Engine` · `DAG` · `Task Orchestration` · `Parallel Execution` · `Retry Policy` · `Timeout Control` · `Conditional Branching` · `Cron Scheduling` · `LLM Pipeline` · `Tavily API` · `Feishu Webhook`

### 简历项目描述模板

> **Phone Intel — 基于 Prefect 工作流的竞品情报自动化系统**
> 
> 使用 Prefect 工作流引擎搭建端到端 ETL + LLM 分析流水线。通过 `@flow`/`@task` 实现 DAG 编排，`task.submit()` 实现 4 品牌并行搜索，`retries=2` + `timeout_seconds=30` 保障 API 稳定性，条件分支跳过空结果 LLM 调用以节约成本。每日定时调度自动产出竞品日报，推送至飞书。可作为通用情报监控模板复用。
>
> *GitHub: github.com/jackal-black/phone-intel*

---

## 扩展方向

| 方向 | 实现 | 简历加分点 |
|------|------|-----------|
| **Prefect Server 部署** | Docker Compose 启动 Prefect Server + Worker | "分布式工作流部署" |
| **子工作流 (Subflow)** | 每个品牌独立子工作流 | "Workflow 嵌套与复用" |
| **缓存策略** | `cache_key_fn=task_input_hash` | "幂等性与增量计算" |
| **异步 Task** | `async def` + `httpx.AsyncClient` | "异步并发优化" |

---

## License

MIT
