"""High-performance local daemon for anix-ghost."""
from __future__ import annotations

import json
import logging
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from . import __version__
from .engine.ai import forge_command
from .engine.context import ProjectContext, extract_context
from .engine.heuristics import predict_heuristics
from .engine.history import HistoryIndex
from .settings import Settings

logger = logging.getLogger("anix_ghost.server")


class GhostHandler(BaseHTTPRequestHandler):
    server: GhostServer  # type annotation

    def log_message(self, format: str, *args: Any) -> None:
        # Suppress default stdout log noise for speed; log to debug only
        logger.debug("%s - " + format, self.address_string(), *args)

    def _send_json(self, status: int, data: dict[str, Any]) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path in ("/health", "/status", "/"):
            self._send_json(200, {
                "status": "ok",
                "service": "anix-ghost",
                "version": __version__,
                "uptime": time.time() - self.server.start_time,
            })
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length) if length > 0 else b"{}"
        try:
            body = json.loads(raw_body.decode("utf-8", errors="ignore"))
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid json"})
            return

        if self.path == "/suggest":
            self._handle_suggest(body)
        elif self.path == "/forge":
            self._handle_forge(body)
        else:
            self._send_json(404, {"error": "not found"})

    def _handle_suggest(self, body: dict[str, Any]) -> None:
        line = str(body.get("line", ""))
        cwd = str(body.get("cwd", "")) or str(Path.cwd())

        # If user is writing ?? prompt, don't trigger regular autocomplete
        if line.strip().startswith("??"):
            self._send_json(200, {"suggestion": None, "type": "forge"})
            return

        ctx = self.server.get_cached_context(cwd)
        suggestion = predict_heuristics(line, ctx, self.server.history)

        if suggestion:
            self._send_json(200, {
                "text": suggestion.text,
                "suffix": suggestion.suffix,
                "source": suggestion.source,
                "confidence": suggestion.confidence,
            })
        else:
            self._send_json(200, {"suggestion": None})

    def _handle_forge(self, body: dict[str, Any]) -> None:
        prompt = str(body.get("prompt", "")).strip()
        shell = str(body.get("shell", "powershell" if sys.platform == "win32" else "bash"))
        cmd, explanation = forge_command(prompt, shell, self.server.settings)
        self._send_json(200, {
            "command": cmd,
            "explanation": explanation,
        })


class GhostServer(ThreadingHTTPServer):
    def __init__(self, host: str = "127.0.0.1", port: int = 8766, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.load()
        super().__init__((host, port), GhostHandler)
        self.start_time = time.time()
        self.history = HistoryIndex()
        self._context_cache: dict[str, tuple[float, ProjectContext]] = {}

    def get_cached_context(self, cwd: str) -> ProjectContext:
        """Cache context per cwd for 1 second to avoid repeated filesystem scans."""
        now = time.time()
        cached = self._context_cache.get(cwd)
        if cached and (now - cached[0]) < 1.0:
            return cached[1]
        ctx = extract_context(cwd)
        self._context_cache[cwd] = (now, ctx)
        return ctx


def run_server(port: int = 8766, verbose: bool = False) -> None:
    settings = Settings.load()
    port = port or settings.port
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="[%(asctime)s] %(levelname)s: %(message)s")

    server = GhostServer(port=port, settings=settings)
    print(f"👻 ANIX Ghost daemon running on http://127.0.0.1:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping daemon...")
    finally:
        server.server_close()
