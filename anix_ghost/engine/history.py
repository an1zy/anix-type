"""Shell history reader & frecency indexer.

Parses PowerShell PSReadLine history on Windows and ~/.bash_history / ~/.zsh_history on Unix.
Caches history in-memory and reloads only when the file modification time changes.
"""
from __future__ import annotations

import os
import sys
from collections import Counter
from pathlib import Path


def get_history_file() -> Path | None:
    """Detect shell history file path for the current OS."""
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            ps_history = Path(appdata) / "Microsoft" / "Windows" / "PowerShell" / "PSReadLine" / "ConsoleHost_history.txt"
            if ps_history.is_file():
                return ps_history
    else:
        home = Path.home()
        for cand in [home / ".zsh_history", home / ".bash_history"]:
            if cand.is_file():
                return cand
    return None


class HistoryIndex:
    """In-memory indexed history with frecency (frequency + recency) ranking."""

    def __init__(self, history_file: Path | None = None) -> None:
        self.history_file = history_file or get_history_file()
        self._last_mtime: float = 0.0
        self._commands: list[str] = []
        self._frequencies: Counter[str] = Counter()

    def refresh_if_needed(self) -> None:
        if not self.history_file or not self.history_file.is_file():
            return
        try:
            mtime = self.history_file.stat().st_mtime
            if mtime == self._last_mtime:
                return
            self._last_mtime = mtime
            lines = self.history_file.read_text(encoding="utf-8", errors="ignore").splitlines()

            # Take the last 3000 lines, filter empty/comments
            clean = []
            for line in lines[-3000:]:
                s = line.strip()
                if s and not s.startswith("#") and len(s) > 1:
                    clean.append(s)

            self._frequencies = Counter(clean)
            # Ordered unique: newest commands first
            seen = set()
            ordered = []
            for cmd in reversed(clean):
                if cmd not in seen:
                    seen.add(cmd)
                    ordered.append(cmd)
            self._commands = ordered
        except OSError:
            pass

    def match(self, prefix: str, max_results: int = 5) -> list[str]:
        """Find commands matching prefix, ranked by frequency and recency."""
        self.refresh_if_needed()
        if not prefix.strip():
            return []

        prefix_lower = prefix.lower()
        exact_prefix_matches = []
        word_matches = []

        for idx, cmd in enumerate(self._commands):
            cmd_lower = cmd.lower()
            if cmd_lower == prefix_lower:
                continue  # already typed exactly this
            if cmd_lower.startswith(prefix_lower):
                # Score combines recency (idx lower is newer) and frequency
                freq = self._frequencies[cmd]
                score = (freq * 10) - (idx * 0.05)
                exact_prefix_matches.append((score, cmd))
            elif prefix_lower in cmd_lower and len(prefix) >= 3:
                freq = self._frequencies[cmd]
                score = (freq * 5) - (idx * 0.1)
                word_matches.append((score, cmd))

        exact_prefix_matches.sort(key=lambda x: x[0], reverse=True)
        word_matches.sort(key=lambda x: x[0], reverse=True)

        results = [cmd for _, cmd in exact_prefix_matches]
        for _, cmd in word_matches:
            if cmd not in results:
                results.append(cmd)

        return results[:max_results]
