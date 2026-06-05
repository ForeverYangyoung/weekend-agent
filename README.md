# Weekend Agent

美团 AI Hackathon · 赛题 06：**本地探索 — 周末闲时活动规划 Agent**

一句话描述周末出行需求，Agent 完成「画像 → 检索 → 规划 → 校验 → 预检 → 下单 → 行程卡」闭环。

## 快速开始

```powershell
# 1. 后端环境（项目根目录）
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .

# 2. 前端构建
cd frontend-v2
npm install
npm run build
cd ..

# 3. 一键启动
python app.py
# 打开 http://127.0.0.1:8000
```

**开发模式**（前端热更新）：

```powershell
# 终端 1
python -m backend

# 终端 2
cd frontend-v2 && npm run dev
# 打开 http://localhost:3000
```

**CLI 终端演示**（答辩逐行 trace）：

```powershell
python -m backend.demo --scene family
python -m backend.demo --scene family --fail 吃   # 补偿链演示
```

## 项目结构

| 路径 | 说明 |
|------|------|
| `backend/` | LangGraph 状态机、FastAPI、Mock 美团 API |
| `frontend-v2/` | React 答辩 UI（SSE 对接） |
| `planner/` | 规划引擎子模块（顺路活动、时间轴） |
| `01-题目工程拆解.md` | 赛题 PRD / Mock API 契约 |
| `02.架构和agent.md` | 架构与 Agent 设计 |
| `03.细节实现.md` | 已落地亮点 |
| `04.第一阶段展示.md` | CLI 跑通记录与答辩话术 |

## API

| 端点 | 说明 |
|------|------|
| `GET /` | React 前端 |
| `GET /health` | 健康检查 |
| `POST /v1/agent/stream` | 规划 + 预检（HIL 暂停，待确认） |
| `POST /v1/agent/replan` | 点改偏好后从 Researcher 重跑 |
| `POST /v1/agent/confirm` | 用户确认后真实下单 |
| `GET /mock-meituan/*` | Mock 美团 HTTP API |

详细 Mock 接口见 [docs/mock-api.md](docs/mock-api.md)。
