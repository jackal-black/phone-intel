# 📱 Phone Intel — 项目总结

> **竞品情报自动化 DAG 工作流**
> 
> Prefect 工作流引擎 + asyncio 异步 IO + LLM 情报分析 + 飞书推送

---

## 一、项目背景

### 痛点

手机行业的竞品监控是一项高频、重复、耗时的工作。市场运营每天需要手动浏览 OPPO、vivo、华为、iPhone 等多个品牌的新品发布资讯，搜集 → 阅读 → 归类 → 汇总，整个过程约 1.5 小时/天。信息分散在新闻站、自媒体、官网多个渠道，容易遗漏。

### 目标

搭建一套全自动情报流水线：**数据采集 → 去重归类 → 摘要生成 → 消息推送**，全流程零人工介入。

### 为什么用 Workflow 引擎

| 方案 | 问题 | 结论 |
|------|------|------|
| Shell 脚本 + curl | 无重试、无超时、线性执行、失败全挂 | ❌ |
| Python 线性脚本 | 串行搜索慢、API 超时会卡死、无调度 | ❌ |
| **Prefect DAG 工作流** | **Task 级容错、并行执行、定时调度、可观测** | ✅ |

---

## 二、技术架构

### 整体流程

```
┌────────────────────────────────────────────────────────┐
│                    Prefect Flow                         │
│                                                         │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐         │
│   │ Search    │    │ Analyze  │    │ Notify   │         │
│   │ Task × 4  │───→│ Task     │───→│ Task     │         │
│   │ (并行)    │    │ (LLM)    │    │ (飞书)   │         │
│   └──────────┘    └──────────┘    └──────────┘         │
│         │               │               │               │
│   ┌─────┴─────┐   ┌────┴────┐   ┌─────┴──────┐        │
│   │ Tavily    │   │DeepSeek │   │ Feishu     │         │
│   │ Search API│   │ Chat    │   │ Webhook    │         │
│   └───────────┘   └─────────┘   └────────────┘        │
└────────────────────────────────────────────────────────┘
         ↑              ↑              ↑
      retries=2      retries=1     timeout=10s
      timeout=30s   timeout=90s
```

### Workflow 节点设计

| Task | 类型 | 职责 | 容错 |
|------|------|------|------|
| `task_search_brand` × 4 | **async** | Tavily API 并发搜索 | `retries=2` + `timeout=30s` |
| `task_flatten_results` | **sync** | 合并排序（纯 CPU） | 无需重试 |
| `task_analyze` | **async** | LLM 去重/归类/摘要 | `retries=1` + `timeout=90s` |
| `task_notify` | **async** | 飞书卡片推送 | 不重试，降级打印 |

### 依赖关系（DAG 拓扑）

```
search_oppo ─┐
search_vivo  ─┤
search_华为  ─┤──→ flatten → analyze → notify
search_iPhone┘
                ↑            ↑         ↑
              无依赖      依赖flatten 依赖analyze
              (并行执行)
```

---

## 三、核心设计决策

### 3.1 为什么选 Prefect 而非 Temporal

| 维度 | Prefect | Temporal |
|------|---------|----------|
| 学习成本 | 低：`@flow`/`@task` 装饰器 | 高：Workflow/Activity/Worker 概念 |
| 运行环境 | `pip install` 即可 | 需要 Docker 启动 Temporal Server |
| 适用场景 | 数据管道、定时任务 | 微服务编排、长时运行状态工作流 |
| 本项目匹配度 | ✅ 刚好 | ❌ 过重 |

结论：Prefect 对本项目的**批处理 + 定时调度**场景更合适，且代码更简洁，适合简历展示。

### 3.2 为什么用 async 而非 sync

从 `requests` 升级到 `httpx.AsyncClient` 的原因：

| 指标 | sync (requests) | async (httpx) |
|------|-----------------|---------------|
| 4 品牌搜索耗时 | ~8s（串行） | ~3s（并行） |
| 超时中断 | ❌ 线程无法中断 | ✅ event loop 可取消 |
| Prefect 兼容性 | ⚠️ timeout warning | ✅ 原生支持 |
| 代码复杂度 | 低 | 略高，但可接受 |

结论：IO 密集型场景**async 收益明显**，且消除了 Prefect 的超时 warning，代码质量更高。

### 3.3 为什么保留 sync `task_flatten_results`

合并排序是纯 CPU 运算（内存中排序 20 条记录），async 没有任何收益。**同步/异步混用**更符合工程实际——只在 IO 边界用 async，CPU 运算保持 sync。

### 3.4 条件分支设计

```python
async def task_analyze(results, ...):
    if not results:  # ← 条件分支
        return "## 今日无相关资讯。"
    return await analyze_news(results, ...)
```

意义：Tavily 搜索可能返回空结果（凌晨、休市等），浪费 LLM Token。条件分支**提前返回**，每次节省 ~1,000 tokens。

---

## 四、技术亮点

### 4.1 异步并行搜索

```python
# 4 个搜索任务同时提交到事件循环
futures = {}
for brand in config.brands:
    futures[brand] = task_search_brand.submit(brand, config.tavily_api_key)

# 按品牌顺序收集（已完成的任务直接取结果）
results_by_brand = [futures[b].result() for b in config.brands]
```

`task.submit()` 将 async task 提交到 Prefect 的事件循环，4 个 HTTP 请求同时发送，总耗时 ≈ 最慢的单次请求（~3s），而不是 4 倍。

### 4.2 可中断超时

```python
@task(timeout_seconds=30)
async def task_search_brand(brand, api_key):
    return await search_brand(brand, api_key)
```

sync task 的超时在线程中失效（不能中断 `requests.get`），async task 在 event loop 中可以被 `asyncio.wait_for` 真正取消。

### 4.3 自动重试 + 退避

```python
@task(retries=2, retry_delay_seconds=10)
```

Tavily API / LLM API 均为网络调用，可能因限流、网络抖动超时。重试 2 次 + 10 秒退避覆盖绝大多数瞬时故障。

### 4.4 降级策略

```python
except httpx.HTTPError as e:
    logger.error("❌ LLM 调用失败: %s", e)
    return _fallback_summary(results, today)  # ← 降级：原始结果拼接
```

LLM API 不可用时，不崩溃，返回原始搜索结果拼接。**宁可给用户看原始数据，也不让流程空转报错**。

---



## 六、项目结构

```
phone-intel/
├── workflow.py              # @flow + @task DAG 定义
├── main.py                  # 入口：运行 / 调度
├── phone_monitor/
│   ├── searcher.py          # async Tavily 搜索
│   ├── analyzer.py          # async LLM 分析
│   ├── notifier.py          # async 飞书推送
│   └── config.py            # .env 配置管理
├── requirements.txt         # prefect + httpx
├── README.md                # 用户文档
├── SUMMARY.md               # ← 本文档
├── .env.example             # 配置模板
├── .gitignore
└── setup.sh
```

---

## 七、扩展方向

| 方向 | 思路 | 工程价值 |
|------|------|----------|
| **子工作流** | 每个品牌作为一个 Subflow | Workflow 嵌套复用、代码隔离 |
| **缓存** | `cache_key_fn=task_input_hash` | 相同输入不重复调用 API |
| **历史数据库** | SQLite 存储历史日报 | 趋势分析、数据回溯 |
| **Prefect Server** | Docker Compose 部署 | 持久化编排、团队协作 |
| **异步全链路** | `async for` 流式输出 LLM | 首 token 延迟优化 |
| **多渠道** | 通知器抽象层 → 飞书/钉钉/邮件 | 单一职责、开闭原则 |

---

*项目地址: [github.com/jackal-black/phone-intel](https://github.com/jackal-black/phone-intel)*
*文档版本: 2026-06*
