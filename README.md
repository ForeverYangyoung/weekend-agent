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

## 答辩演示（推荐 UI）

左手机 + 右 Trace，双轨场景：

| 场景 | 操作 | 右侧 Trace 看点 |
|------|------|----------------|
| **家庭** | 选家庭场景 → 开始规划 → 确认下单 | 候选榜 / 方案对比 / 加餐 `deliver_to_poi_id` |
| **朋友** | 选朋友场景（4 人）→ 开始规划 | 姜虎东 DryRun 满座 → Recovery 换炙烤大叔 |

**CLI 备用**（无浏览器时）：

```powershell
python -m backend.demo --scene family
python -m backend.demo --scene friends
python -m backend.demo --scene family --fail 吃   # 确认后补偿链
```

## 文档（真源）

| 文件 | 用途 |
|------|------|
| `01-题目工程拆解.md` | 赛题 PRD、Mock API、场景定义 |
| `02.架构和agent.md` | LangGraph 拓扑、Agent 职责、State |
| `03.细节实现.md` | 已落地功能对照表 |
| `docs/mock-api.md` | Mock HTTP 端点与 curl |

## 项目结构

| 路径 | 说明 |
|------|------|
| `backend/` | LangGraph、FastAPI、SSE、Mock 美团 |
| `frontend-v2/` | React 答辩 UI |
| `planner/` | 顺路活动目录等规划辅助模块 |
| `tests/` | API 与场景回归 |

## API

| 端点 | 说明 |
|------|------|
| `GET /` | React 前端 |
| `POST /v1/agent/stream` | 规划 + 预检（HIL 暂停） |
| `POST /v1/agent/replan` | 改偏好后重规划 |
| `POST /v1/agent/confirm` | 确认后下单 |
| `GET /mock-meituan/*` | Mock 美团 HTTP |

Mock 接口详情见 [docs/mock-api.md](docs/mock-api.md)。
