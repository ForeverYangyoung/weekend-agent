# weekend-agent

[![GitHub](https://img.shields.io/badge/GitHub-ForeverYangyoung%2Fweekend--agent-blue)](https://github.com/ForeverYangyoung/weekend-agent)

美团 AI Hackathon · 赛题 06：**本地探索 — 周末闲时活动规划 Agent**

一句话描述周末出行需求，Agent 完成「画像 → 规划 → 校验 → 模拟执行 → 行程卡通知」闭环（LangGraph + FastAPI SSE）。

## 快速开始

```bash
cd apps/api
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
pip install -e .

# CLI 演示
python -m weekend_agent.demo

# 启动 API + 浏览器测试页
python -m weekend_agent
# 打开 http://127.0.0.1:8000/playground
```

详细接口、SSE、失败注入演示见 [apps/api/README.md](apps/api/README.md)。

## Super Dev（Cursor）

本仓库已接入 Super Dev 流水线（从 `D:\weekend-agent` 迁入配置，**未改动** `apps/api/weekend_agent` 代码）。

| 命令 | 用途 |
|------|------|
| `/super-dev …` | 标准流程：调研 → 三文档 → 确认 → 前端优先 → 后端 |
| `/super-dev-seeai …` | 黑客松快版（推荐答辩 UI） |

- 文档映射：[`.super-dev/WORKFLOW.md`](.super-dev/WORKFLOW.md)
- PRD / 架构真源：根目录 `01`、`02`；生成物在 `output/`（见 `output/README.md`）

示例：

```text
/super-dev-seeai 赛题06；01/02 为真源；P0 答辩前端对接现有 SSE；不重写后端。
```

## 仓库结构

| 路径 | 说明 |
|------|------|
| `apps/api/weekend_agent/` | LangGraph 状态机、FastAPI、内置 Playground |
| `01-题目工程拆解.md` | 赛题 PRD / Mock API 契约 |
| `02.架构和agent.md` | 架构与 Agent 设计 |
| `03.细节实现.md` | 已落地亮点 vs 原队友设计、困难项清单 |
| `04.第一阶段展示.md` | PyCharm 跑通步骤 + 逐节点输入输出串讲 |
| `.cursor/commands/` | Super Dev 斜杠命令 |
| `docs/` | 索引、质量门禁、Demo 剧本 |

## 在线演示

本地启动后访问：`http://127.0.0.1:8000/playground`（需先运行 `python -m weekend_agent`）。
