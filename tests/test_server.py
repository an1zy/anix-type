import json
import threading
import time
import urllib.request
from pathlib import Path
from anix_ghost.server import GhostServer
from anix_ghost.settings import Settings


def test_server_suggest_endpoint(tmp_path: Path):
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")

    settings = Settings(port=18766)
    server = GhostServer(port=18766, settings=settings)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.1)

    try:
        # 1. Health check
        with urllib.request.urlopen("http://127.0.0.1:18766/health") as resp:
            data = json.loads(resp.read().decode())
            assert data["status"] == "ok"
            assert data["service"] == "anix-ghost"

        # 2. Suggestion check
        req_data = json.dumps({"line": "git p", "cwd": str(tmp_path)}).encode()
        req = urllib.request.Request(
            "http://127.0.0.1:18766/suggest",
            data=req_data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            res = json.loads(resp.read().decode())
            assert res["text"] == "git push origin main"
            assert res["suffix"] == "ush origin main"
            assert res["source"] == "git"

    finally:
        server.shutdown()
        server.server_close()
