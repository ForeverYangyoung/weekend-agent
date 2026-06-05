# LangGraph State

与代码 [`backend/state.py`](../backend/state.py) 对齐。

| 字段 | 说明 |
|------|------|
| `user_input` | 用户原始一句话 |
| `group_profile` | Profiler 输出的 `GroupProfile` |
| `plan` | Planner 输出的 `Plan` |
| `plan_iteration` | 重规划次数（兜底用） |
| `critic_feedback` | Critic 校验结果 |
| `dry_run_calls` | DryRun 阶段工具调用 |
| `executed_calls` | Executor 已执行调用 |
| `failed_calls` | 失败调用（补偿链输入） |
| `user_confirmed` | HIL 用户是否确认方案 |
| `summary_card` | Notifier 行程卡 |
| `trace` | 节点追踪日志（`operator.add` 累加） |
| `force_failure` | Demo 注入失败阶段 |

架构设计背景见 [`02.架构和agent.md`](../02.架构和agent.md) 第 6 节。
