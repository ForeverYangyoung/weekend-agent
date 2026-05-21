"""兼容 shim：保留旧 import 路径 `weekend_agent.tools.mock_client`。

新版业务逻辑已搬到 `weekend_agent.mock_meituan.backend`，并且通过 HTTP 暴露给
Agent。本文件只把名字转发过去，确保老代码 / 老测试照样能 `from .. import
reset_mock_backend` / `get_mock_backend`。
"""
from __future__ import annotations

from weekend_agent.mock_meituan.backend import (
    ALWAYS_FULL_POIS,
    MockBackend,
    get_mock_backend,
    reset_mock_backend,
)

__all__ = [
    "ALWAYS_FULL_POIS",
    "MockBackend",
    "get_mock_backend",
    "reset_mock_backend",
]
