"""Weekend Agent — 一键启动: python app.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import uvicorn

if __name__ == "__main__":
    print("\n  \033[96mWeekend Agent 启动中…\033[0m\n")
    print("  \033[4m\033]8;;http://127.0.0.1:8000/playground\ahttp://127.0.0.1:8000/playground\033]8;;\a\033[0m  \033[90m(点击打开浏览器测试页)\033[0m\n")

    uvicorn.run(
        "backend.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
# ## 首次安装
# cd d:\weekend-agent
# .venv\Scripts\Activate.ps1
# pip install -e . -i https://pypi.tuna.tsinghua.edu.cn/simple

# # 启动（终端会显示可点击链接）
# python app.py

# # CLI 演示
# python -m backend.demo
