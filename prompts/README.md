# Prompts

将 Agent 用到的 system / user 模板外置到此目录，与代码中的加载路径保持一致。

建议文件（待从 `backend/nodes/` 抽离）：

- `profiler.md`
- `planner.md`
- `critic.md`

当前 Profiler 为规则 stub，接 LLM 时优先在此维护 prompt，避免散落在 Python 字符串中。
