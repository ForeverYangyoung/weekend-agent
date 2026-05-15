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

## 仓库结构

| 路径 | 说明 |
|------|------|
| `apps/api/weekend_agent/` | LangGraph 状态机、FastAPI、内置 Playground |
| `01-题目工程拆解.md` | 赛题 PRD / Mock API 契约 |
| `02.架构和agent.md` | 架构与 Agent 设计 |

## 在线演示

本地启动后访问：`http://127.0.0.1:8000/playground`（需先运行 `python -m weekend_agent`）。
