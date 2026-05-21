"""假后台（Mock）与 Tool 注册表。

DryRun / Executor / Compensator 都通过这里调用，而不是在节点里写「假装成功」。
"""

from weekend_agent.tools.errors import ToolError
from weekend_agent.tools.registry import ToolContext, invoke
from weekend_agent.tools.plan_mapping import plan_to_dry_run_calls

__all__ = [
    "ToolError",
    "ToolContext",
    "invoke",
    "plan_to_dry_run_calls",
]
