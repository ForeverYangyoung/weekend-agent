# Tool Schemas

Mock Tool 的入参 / 出参定义以 PRD 为准：

- [`01-题目工程拆解.md`](../01-题目工程拆解.md) — 搜索「Mock」「Tool」「API」相关章节

实现与调用链：

- `apps/api/weekend_agent/nodes/`（`planner`、`executor`、`dry_run` 等）
- `apps/api/weekend_agent/schemas.py`

后续可在此目录补充与 Pydantic 模型一一对应的 JSON 示例。
