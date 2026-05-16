"""NewsMonitor Web 入口"""
import os
import sys

# Windows UTF-8 编码修复（必须在所有 import 之前）
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("PYTHONUTF8", "1")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# 禁用系统代理
os.environ.pop("HTTP_PROXY", None)
os.environ.pop("HTTPS_PROXY", None)
os.environ.pop("http_proxy", None)
os.environ.pop("https_proxy", None)
os.environ.pop("ALL_PROXY", None)
os.environ.pop("all_proxy", None)
os.environ["NO_PROXY"] = "*"

import requests
requests.Session.trust_env = False

from pathlib import Path

# 确保 web 包可导入
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from web import create_app

app = create_app()

if __name__ == "__main__":
    print("=" * 50)
    print("  NewsMonitor Web Server")
    print("  http://localhost:5000")
    print("=" * 50)
    app.run(host="0.0.0.0", port=5000, threaded=True, debug=False)
