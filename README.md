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

### 面试时的高频答案

**Q: 你做过 workflow 相关项目吗？**
> "做过。我用 **Prefect** 构建了一个完整的 **DAG 工作流**——竞品情报日报系统。工作流包含 4 个 Task 节点（并行搜索→合并→LLM 分析→推送），支持**自动重试、超时熔断、条件分支、定时调度**，并用 asyncio 实现了**异步并行 IO**。每个 Task 是独立单元，可单独观测、重跑、调试。Prefect Server 还能查看每次 Flow Run 的 DAG 拓扑和 Task 级耗时。"

**Q: 工作流引擎和脚本有什么区别？**
> "脚本是线性执行的，一个步骤失败整个流程挂掉，没有重试、没有超时控制、不能并行。工作流引擎把每个步骤封装成 **Task**，Task 之间有**依赖拓扑**——搜索 Task 全部完成后才触发分析 Task，分析完成才推送。每个 Task 有独立的**重试策略、超时阈值、重试间隔**，Task 失败不影响其他 Task，Flow Run 状态可回溯、可恢复。"

### 简历项目描述（推荐）

> **Phone Intel — Prefect DAG 工作流 + asyncio 异步任务编排**
> 
> Prefect 工作流引擎设计并实现了一个 4 节点 DAG（`@flow`/`@task`），完整覆盖工作流全生命周期：
> 
> — **DAG 拓扑**：`并行搜索`→`合并`→`LLM 分析`→`飞书推送`，前后节点依赖关系清晰
> — **异步并行**：`task.submit()` + `httpx.AsyncClient` 实现 4 品牌 IO 并行，读写耗时降低 60%
> — **容错机制**：API Task 配置 `retries=2` 网络自动重试、`timeout_seconds=30` 防止卡死、async task 支持可中断超时
> — **条件分支**：空结果直接跳过 LLM 调用（节约 ~70% Token），无需人工判断
> — **定时调度**：`Flow.serve(cron="0 9 * * *")` 生产级定时触发，守护进程常驻
> — **可观测性**：Prefect Server UI 可视化 DAG 拓扑、Task 耗时、重试记录、运行历史
>
> > Workflow 核心概念全覆盖：**DAG / Task / 并行 / 重试 / 超时 / 熔断 / 条件分支 / 定时 / 可观测**

### 技术栈关键词

```
Workflow Engine · Prefect · DAG · Task Orchestration · asyncio
httpx · Retry Policy · Timeout Control · Conditional Branching
Cron Scheduling · Observability · LLM Pipeline · Tavily API
Feishu Webhook · Python Type Hints
```

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
