"""Weekend Agent — python app.py"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import uvicorn

ROOT = Path(__file__).resolve().parent
FRONTEND_DIST = ROOT / "frontend-v2" / "dist"

if __name__ == "__main__":
    if not (FRONTEND_DIST / "index.html").is_file():
        print("构建前端...")
        try:
            subprocess.run(["npm", "run", "build"], cwd=str(FRONTEND_DIST.parent), check=True)
        except Exception:
            print("前端构建失败，请手动: cd frontend-v2 && npm run build")

    print("\n  http://127.0.0.1:8000\n")
    uvicorn.run("backend.server:app", host="0.0.0.0", port=8000, reload=True)
