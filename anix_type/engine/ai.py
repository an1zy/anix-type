"""AI Command Forge: turns natural language into exact shell commands via Groq / Ollama / heuristics."""
from __future__ import annotations

import json
import re
import urllib.request
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..settings import Settings


def _forge_offline(prompt: str, shell: str) -> str | None:
    """Instant offline heuristic forge for high-frequency dev operations."""
    p = prompt.lower().strip()

    # 1. Git commit rollback / undo
    if ("откат" in p or "отмен" in p or "вернуть" in p or "undo" in p or "revert" in p) and ("коммит" in p or "commit" in p):
        if any(w in p for w in ("оставить", "сохранить", "soft", "файлы", "сохраняя")):
            return "git reset --soft HEAD~1"
        if any(w in p for w in ("жестк", "полност", "стереть", "удалить", "hard", "чист")):
            return "git reset --hard HEAD~1"
        return "git reset --soft HEAD~1"

    # Git amend
    if ("изменить" in p or "переписать" in p or "дополнить" in p or "amend" in p) and ("коммит" in p or "commit" in p):
        return "git commit --amend"

    # Git stash
    if "stash" in p or "спрятать" in p or "сохранить изменения" in p:
        if "вернуть" in p or "pop" in p or "достать" in p or "применить" in p:
            return "git stash pop"
        if "список" in p or "list" in p:
            return "git stash list"
        return "git stash"

    # Git discard changes
    if ("сбросить" in p or "отменить" in p or "discard" in p) and ("изменения" in p or "changes" in p or "файлы" in p):
        return "git restore ."

    # Git branch
    if "ветк" in p or "branch" in p:
        words = prompt.split()
        if "создать" in p or "новая" in p or "new" in p or "create" in p:
            name = words[-1] if words and words[-1].isascii() and words[-1].replace("-", "").isalnum() else "feature"
            return f"git checkout -b {name}"
        if "удалить" in p or "delete" in p or "remove" in p:
            name = words[-1] if words and words[-1].isascii() and words[-1].replace("-", "").isalnum() else "<branch>"
            return f"git branch -d {name}"
        if "все" in p or "список" in p or "list" in p:
            return "git branch -a"

    # Git logs / commits history
    if ("логи" in p or "история" in p or "коммиты" in p or "log" in p) and ("коммит" in p or "commit" in p or "репо" in p):
        return "git log --oneline -n 10"

    # Git status
    if p in ("статус", "status", "git status", "что изменилось"):
        return "git status"

    # Kill process by port
    if ("убить" in p or "прибить" in p or "закрыть" in p or "kill" in p) and ("порт" in p or "port" in p):
        m = re.search(r"\b(\d{2,5})\b", p)
        port = m.group(1) if m else "8080"
        if shell == "powershell":
            return f"Stop-Process -Id (Get-NetTCPConnection -LocalPort {port}).OwningProcess -Force"
        return f"kill -9 $(lsof -t -i:{port})"

    # Folder size
    if "размер" in p and ("папк" in p or "директор" in p or "диск" in p or "folder" in p or "size" in p):
        if shell == "powershell":
            return "(Get-ChildItem -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1MB"
        return "du -sh ."

    # Find file
    if ("найти" in p or "поиск" in p or "find" in p) and ("файл" in p or "file" in p):
        words = prompt.split()
        target = words[-1] if words else "*.py"
        if shell == "powershell":
            return f'Get-ChildItem -Recurse -Filter "*{target}*"'
        return f'find . -name "*{target}*"'

    # Python venv
    if "venv" in p or "окружение" in p or "виртуальн" in p:
        if "создать" in p or "create" in p or "new" in p:
            return "python -m venv .venv"
        if "активир" in p or "activate" in p:
            return r".\.venv\Scripts\Activate.ps1" if shell == "powershell" else "source .venv/bin/activate"

    # Pip purge / requirements
    if "pip" in p:
        if "очистить" in p or "кэш" in p or "cache" in p:
            return "pip cache purge"
        if "заморозить" in p or "freeze" in p or "requirements" in p:
            return "pip freeze > requirements.txt"
        if "обновить" in p or "upgrade" in p:
            return "python -m pip install --upgrade pip"

    # Pytest
    if "тест" in p or "test" in p or "pytest" in p:
        return "pytest -q"

    # Docker
    if "docker" in p or "докер" in p:
        if "остановить" in p and "все" in p:
            return "docker stop $(docker ps -q)"
        if "удалить все" in p or "prune" in p:
            return "docker system prune -a --volumes"
        if "логи" in p or "logs" in p:
            return "docker compose logs -f"

    return None


def forge_command(prompt: str, shell: str = "powershell", settings: Settings | None = None) -> tuple[str, str]:
    """Convert natural language prompt to a shell command.

    Returns (command, explanation).
    """
    if not settings:
        from ..settings import Settings
        settings = Settings.load()

    clean = prompt.strip()
    if clean.startswith("??"):
        clean = clean[2:].strip()

    if not clean:
        return "", ""

    # 0. Check instant offline heuristic forge (<0.1ms)
    offline = _forge_offline(clean, shell)
    if offline:
        return offline, "Instant heuristic forge"

    # 1. Try Groq (ultra fast free tier)
    if settings.ai_provider == "groq" and settings.groq_api_key:
        try:
            return _call_groq(clean, shell, settings)
        except Exception as e:
            return "", f"Groq error: {e}"

    # 2. Try Ollama (local)
    if settings.ai_provider == "ollama":
        try:
            return _call_ollama(clean, shell, settings)
        except Exception as e:
            return "", f"Ollama error: {e}"

    # 3. Fallback when no key is set
    return "", "AI is not configured. Set free Groq key via `anix-type config --groq-key <key>` or run Ollama."


def _call_groq(prompt: str, shell: str, settings: Settings) -> tuple[str, str]:
    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        "model": settings.model or "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system",
                "content": (
                    f"You are a terminal command generator for {shell}. "
                    "Output ONLY the single executable command string. "
                    "No markdown code blocks, no backticks, no explanations, no prefix. "
                    "Just the exact shell command that accomplishes the task."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "max_tokens": 128,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.groq_api_key}",
            "Content-Type": "application/json",
            "User-Agent": "anix-ghost",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=3.5) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        raw = data["choices"][0]["message"]["content"].strip()
        # Clean potential markdown backticks if model ignored instructions
        clean_cmd = raw.replace("```bash", "").replace("```powershell", "").replace("```", "").strip()
        clean_cmd = clean_cmd.splitlines()[0] if clean_cmd.splitlines() else clean_cmd
        return clean_cmd, "Generated via Groq (free)"


def _call_ollama(prompt: str, shell: str, settings: Settings) -> tuple[str, str]:
    url = f"{settings.ollama_url.rstrip('/')}/api/generate"
    payload = {
        "model": settings.model or "qwen2.5-coder:1.5b",
        "prompt": (
            f"Convert this to a single {shell} command. Output ONLY the command, nothing else:\n{prompt}"
        ),
        "stream": False,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=4.0) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        raw = data.get("response", "").strip()
        clean_cmd = raw.replace("```bash", "").replace("```powershell", "").replace("```", "").strip()
        clean_cmd = clean_cmd.splitlines()[0] if clean_cmd.splitlines() else clean_cmd
        return clean_cmd, "Generated via local Ollama"
