# Super Dev · 美团六（weekend-agent）工作流映射

> 本仓库已合并 Super Dev 治理层。**代码真源**在 `backend/`；**需求/架构真源**在根目录 `01`、`02`。

## 文档真源（Canonical）

| Super Dev 期望路径 | 本仓库真源 | 说明 |
|-------------------|-----------|------|
| `output/*-prd.md` | [`01-题目工程拆解.md`](../01-题目工程拆解.md) | 赛题 PRD、Mock API、场景 A/B、NFR |
| `output/*-architecture.md` | [`02.架构和agent.md`](../02.架构和agent.md) | Profiler / Planner / Executor、State、打分 |
| `output/*-research.md` | （Super Dev 生成） | 竞品调研；写入 `output/`，不覆盖 01/02 |
| `output/*-uiux.md` | （Super Dev 生成） | 答辩 UI；参考 `frontend-v2/` |

### 同步规则

1. **触发 `/super-dev` 或 `/super-dev-seeai` 时**：先读 01、02；若 `output/weekend-agent-prd.md` 等不存在，可生成**摘要版**到 `output/`（引用 01/02，不复制全文）。
2. **01/02 与 output 冲突时**：以 **01、02 为准**，更新 output 摘要。
3. **docs confirm 门**：用户确认的是「01/02 + output 中 research/uiux 增量」整体方向，而非仅 output 文件。

## 代码真源（Do Not Replace）

| 路径 | 说明 |
|------|------|
| `backend/` | LangGraph、`server.py`、SSE、各 `nodes/*` |
| `backend/state.py` | State 字段见 [`02.架构和agent.md`](../02.架构和agent.md) 第 6 节 |
| `frontend-v2/` | React 答辩 UI |

禁止用空壳脚手架覆盖上述实现。

## 推荐命令（黑客松）

```text
/super-dev-seeai
赛题06周末活动规划。PRD/架构以 01、02 为准。
P0：答辩前端对接现有 API/SSE；后端以 backend/ 为准不重写。
```

## 质量与演示

- 已落地对照：[`03.细节实现.md`](../03.细节实现.md)
- 答辩演示：[`README.md`](../README.md)「答辩演示」节；`python app.py` → `http://127.0.0.1:8000`
