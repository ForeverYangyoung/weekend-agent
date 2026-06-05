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
        print("  [warn] frontend-v2/ 目录不存在，跳过前端构建")
        return False

    if FRONTEND_DIST.is_dir() and (FRONTEND_DIST / "index.html").is_file():
        print("  [ok] 前端产物已存在，跳过构建")
        return True

    print("  [build] 正在构建前端...")
    try:
        subprocess.run(
            ["npm", "run", "build"],
            cwd=str(FRONTEND_DIR),
            check=True,
            capture_output=True,
            text=True,
        )
        print("  [ok] 前端构建完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  [warn] 前端构建失败:\n{e.stderr}")
        return False
    except FileNotFoundError:
        print("  [warn] 未找到 npm，跳过前端构建。请手动执行: cd frontend-v2 && npm run build")
        return False


if __name__ == "__main__":
    print("\n  Weekend Agent 启动中...\n")
    build_frontend()

    print("\n  打开浏览器: http://127.0.0.1:8000/\n")

    # Windows 下 reload=True 易残留双进程，导致 8000 端口卡死、页面白屏
    use_reload = sys.platform != "win32"

    uvicorn.run(
        "backend.server:app",
        host="127.0.0.1",
        port=8000,
        reload=use_reload,
    )
