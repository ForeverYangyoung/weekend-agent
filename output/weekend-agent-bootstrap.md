# weekend-agent · Super Dev Bootstrap

> 首次进入 Super Dev 时读取本文件 + [`.super-dev/WORKFLOW.md`](../.super-dev/WORKFLOW.md)。

## 已锁定的真源

- **PRD / Mock 契约：** `01-题目工程拆解.md`
- **架构 / Agent 设计：** `02.架构和agent.md`
- **后端实现：** `apps/api/weekend_agent/`（LangGraph + FastAPI + `/playground`）

## Super Dev 三文档策略

| 文档 | 动作 |
|------|------|
| PRD | 读 01；仅在 `output/weekend-agent-prd.md` 写**增量摘要**（P0 路径、非目标、主动放弃项） |
| Architecture | 读 02；仅在 `output/weekend-agent-architecture.md` 写**与前端/联调相关**的增量 |
| UIUX | 读 `playground.html` + 用户需求；在 `output/weekend-agent-uiux.md` **新建**完整 UI 方案 |
| Research | 在 `output/weekend-agent-research.md` **新建** |

## 默认约束（黑客松）

- 作品类型：**工具类**（任务完成型 Agent，非纯聊天壳）
- 不重写已有 LangGraph 节点；前端对接现有 SSE/API
- 主动放弃（除非用户明确要求）：真 Redis、真支付、完整账号体系

## 确认门话术示例

用户确认文档后回复：`确认，按 01/02 与 output uiux 执行。`
