"""Weekend Agent — 一键启动: python app.py"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import uvicorn

PROJECT_ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = PROJECT_ROOT / "frontend-v2"
FRONTEND_DIST = FRONTEND_DIR / "dist"


def build_frontend() -> bool:
    """构建前端产物；失败时返回 False 但不阻止后端启动。"""
    if not FRONTEND_DIR.is_dir():
        print("  ⚠ frontend-v2/ 目录不存在，跳过前端构建")
        return False

    if FRONTEND_DIST.is_dir() and (FRONTEND_DIST / "index.html").is_file():
        print("  ✓ 前端产物已存在，跳过构建")
        return True

    print("  🔨 正在构建前端...")
    try:
        subprocess.run(
            ["npm", "run", "build"],
            cwd=str(FRONTEND_DIR),
            check=True,
            capture_output=True,
            text=True,
        )
        print("  ✓ 前端构建完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ⚠ 前端构建失败:\n{e.stderr}")
        return False
    except FileNotFoundError:
        print("  ⚠ 未找到 npm，跳过前端构建。请手动执行: cd frontend-v2 && npm run build")
        return False


if __name__ == "__main__":
    print("\n  \033[96mWeekend Agent 启动中…\033[0m\n")
    build_frontend()

    print("\n  \033[4m\033]8;;http://127.0.0.1:8000\ahttp://127.0.0.1:8000\033]8;;\a\033[0m  \033[90m(点击打开)\033[0m\n")

    uvicorn.run(
        "backend.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
