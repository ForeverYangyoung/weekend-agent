"""本地启动 API：python -m weekend_agent"""
from __future__ import annotations

import uvicorn


def main() -> None:
    uvicorn.run(
        "weekend_agent.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()
