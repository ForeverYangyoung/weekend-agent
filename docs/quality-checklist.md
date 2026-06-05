# 质量门禁

答辩 / 交付前勾选（与 01 PRD 和现有实现对齐）：

- [ ] 11 Tools 成功 / 超时 / 失败 Mock 路径可走通
- [ ] LLM JSON：Pydantic 失败 ≤3 次重试 → 模板/规则降级（Profiler stub 已可无 LLM 跑通）
- [ ] DryRun 与 Commit 两阶段分离
- [ ] 部分成功场景行程卡带 ⚠️ 或等价提示
- [ ] `trace` 贯穿节点与 Tool（`state.trace`）
- [ ] CLI：`python -m backend.demo`
- [ ] API + UI：`python app.py` → `/`、SSE 流式
- [ ] 三幕 Demo 剧本可走通（见 [`demo-script.md`](demo-script.md)）
- [ ] `docker compose up` 一键起（待 `docker/` 补齐）
