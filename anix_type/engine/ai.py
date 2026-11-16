"""AI Command Forge: turns natural language into exact shell commands via Groq / Ollama / heuristics."""
from __future__ import annotations

import json
import re
import urllib.request
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..settings import Settings


from ..i18n import t

def _forge_offline(prompt: str, shell: str) -> str | None:
    """Instant offline heuristic forge for high-frequency dev operations (EN + RU)."""
    p = prompt.lower().strip()

    # 1. Git commit rollback / undo
    if ("откат" in p or "отмен" in p or "вернуть" in p or "undo" in p or "rollback" in p or "revert" in p) and ("коммит" in p or "commit" in p):
        if any(w in p for w in ("оставить", "сохранить", "soft", "файлы", "сохраняя", "keep")):
            return "git reset --soft HEAD~1"
        if any(w in p for w in ("жестк", "полност", "стереть", "удалить", "hard", "чист", "discard")):
            return "git reset --hard HEAD~1"
        return "git reset --soft HEAD~1"

    # Git amend
    if ("изменить" in p or "переписать" in p or "дополнить" in p or "amend" in p or "change" in p or "update" in p) and ("коммит" in p or "commit" in p):
        return "git commit --amend"

    # Git stash restore / pop
    if ("вернуть" in p or "достать" in p or "применить" in p or "pop" in p or "restore" in p or "apply" in p) and (
        "изменения" in p or "код" in p or "stash" in p or "стэш" in p or "changes" in p
    ):
        return "git stash pop"

    # Git stash save / list
    if "stash" in p or "спрятать" in p or ("сохранить" in p and "изменения" in p):
        if "список" in p or "list" in p:
            return "git stash list"
        return "git stash"

    # Git discard changes
    if ("сбросить" in p or "отменить" in p or "discard" in p or "revert" in p) and ("изменения" in p or "changes" in p or "файлы" in p or "files" in p):
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
        if "все" in p or "список" in p or "list" in p or "all" in p:
            return "git branch -a"

    # Git push / pull
    if ("запушить" in p or "отправить" in p or "push" in p) and ("коммит" in p or "ветк" in p or "main" in p or "origin" in p or "code" in p or "код" in p):
        return "git push origin main"
    if ("скачать" in p or "подтянуть" in p or "стянуть" in p or "pull" in p) and ("изменен" in p or "ветк" in p or "main" in p or "changes" in p):
        return "git pull origin main"

    # Git logs / commits history
    if ("логи" in p or "история" in p or "коммиты" in p or "log" in p or "history" in p) and ("коммит" in p or "commit" in p or "репо" in p or "git" in p):
        return "git log --oneline -n 10"

    # Git status
    if p in ("статус", "status", "git status", "что изменилось", "what changed"):
        return "git status"

    # Kill process by port
    if ("убить" in p or "прибить" in p or "закрыть" in p or "kill" in p or "stop" in p or "free" in p) and ("порт" in p or "port" in p):
        m = re.search(r"\b(\d{2,5})\b", p)
        port = m.group(1) if m else "8080"
        if shell == "powershell":
            return f"Stop-Process -Id (Get-NetTCPConnection -LocalPort {port}).OwningProcess -Force"
        return f"kill -9 $(lsof -t -i:{port})"

    # Top memory processes
    if ("процесс" in p or "process" in p) and ("памят" in p or "memory" in p or "ram" in p or "working" in p):
        if shell == "powershell":
            return "Get-Process | Sort-Object -Property WorkingSet -Descending | Select-Object -First 5"
        return "ps aux --sort=-%mem | head -n 6"

    # Folder size
    if ("размер" in p or "size" in p) and ("папк" in p or "директор" in p or "диск" in p or "folder" in p or "directory" in p or "dir" in p):
        if shell == "powershell":
            return "(Get-ChildItem -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1MB"
        return "du -sh ."

    # Find file
    if ("найти" in p or "поиск" in p or "find" in p or "search" in p or "locate" in p) and ("файл" in p or "file" in p):
        words = prompt.split()
        target = words[-1] if words else "*.py"
        if shell == "powershell":
            return f'Get-ChildItem -Recurse -Filter "*{target}*"'
        return f'find . -name "*{target}*"'

    # Python venv
    if "venv" in p or "окружение" in p or "виртуальн" in p or "virtualenv" in p:
        if "создать" in p or "create" in p or "new" in p:
            return "python -m venv .venv"
        if "активир" in p or "activate" in p:
            return r".\.venv\Scripts\Activate.ps1" if shell == "powershell" else "source .venv/bin/activate"

    # Pip purge / requirements
    if "pip" in p:
        if "очистить" in p or "кэш" in p or "cache" in p or "purge" in p or "clean" in p:
            return "pip cache purge"
        if "заморозить" in p or "freeze" in p or "requirements" in p:
            return "pip freeze > requirements.txt"
        if "обновить" in p or "upgrade" in p or "update" in p:
            return "python -m pip install --upgrade pip"

    # Pytest
    if "тест" in p or "test" in p or "pytest" in p:
        return "pytest -q"

    # Docker
    if "docker" in p or "докер" in p:
        if "остановить" in p or "stop" in p:
            return "docker stop $(docker ps -q)"
        if "удалить все" in p or "prune" in p or "clean" in p:
            return "docker system prune -a --volumes"
        if "логи" in p or "logs" in p:
            return "docker compose logs -f"

    # Clear screen
    if ("очистить" in p and ("экран" in p or "консоль" in p or "терминал" in p)) or p in ("clear", "cls", "clear screen", "clear console"):
        return "Clear-Host"

    return None


def forge_command(prompt: str, shell: str = "powershell", settings: Settings | None = None) -> tuple[str, str]:
    """Convert natural language prompt to a shell command.

    Returns (command, explanation).
    """
    if not settings:
        from ..settings import Settings
        settings = Settings.load()

    lang = settings.language if settings.language != "auto" else None

    clean = prompt.strip()
    if clean.startswith("??"):
        clean = clean[2:].strip()

    if not clean:
        return "", ""

    # 0. Check instant offline heuristic forge (<0.1ms)
    offline = _forge_offline(clean, shell)
    if offline:
        return offline, t("instant_heuristic", lang=lang)

    # 1. Try Groq (ultra fast free tier)
    if settings.ai_provider == "groq" and settings.groq_api_key:
        try:
            return _call_groq(clean, shell, settings)
        except Exception as e:
            return "", f"Groq error: {e}"

    # 2. Try OpenAI-compatible API (OpenAI, DeepSeek, OpenRouter, Gemini, proxy)
    if (settings.ai_provider in ("openai", "custom") or settings.openai_api_key) and settings.openai_api_key:
        try:
            return _call_openai_compatible(clean, shell, settings)
        except Exception as e:
            return "", f"AI error: {e}"

    # 3. Try Ollama (local)
    if settings.ai_provider == "ollama":
        try:
            return _call_ollama(clean, shell, settings)
        except Exception as e:
            return "", f"Ollama error: {e}"

    # 4. Fallback when no key is set
    return "", t("ai_not_configured", lang=lang)


def _call_openai_compatible(prompt: str, shell: str, settings: Settings) -> tuple[str, str]:
    url = f"{settings.openai_base_url.rstrip('/')}/chat/completions"
    model = settings.model if settings.model and "llama-3.1" not in settings.model else "gpt-4o-mini"
    payload = {
        "model": model,
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
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
            "User-Agent": "anix-type",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        raw = data["choices"][0]["message"]["content"].strip()
        clean_cmd = raw.replace("```bash", "").replace("```powershell", "").replace("```", "").strip()
        clean_cmd = clean_cmd.splitlines()[0] if clean_cmd.splitlines() else clean_cmd
        return clean_cmd, f"Generated via {settings.ai_provider or 'OpenAI-compatible'}"


def _call_groq(prompt: str, shell: str, settings: Settings) -> tuple[str, str]:
    url = "https://api.groq.com/openai/v1/chat/completions"
    lang = settings.language if settings.language != "auto" else None
    payload = {
        "model": settings.model or "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system",
                "content": (
                    f"You are a terminal command generator for {shell}. "
                    "The user request may be in English, Russian, or other languages. "
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
            "User-Agent": "anix-type",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=3.5) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        raw = data["choices"][0]["message"]["content"].strip()
        # Clean potential markdown backticks if model ignored instructions
        clean_cmd = raw.replace("```bash", "").replace("```powershell", "").replace("```", "").strip()
        clean_cmd = clean_cmd.splitlines()[0] if clean_cmd.splitlines() else clean_cmd
        return clean_cmd, t("generated_groq", lang=lang)


def _call_ollama(prompt: str, shell: str, settings: Settings) -> tuple[str, str]:
    url = f"{settings.ollama_url.rstrip('/')}/api/generate"
    lang = settings.language if settings.language != "auto" else None
    payload = {
        "model": settings.model or "qwen2.5-coder:1.5b",
        "prompt": (
            f"You are a command-line expert for {shell}.\n"
            f"Convert the following natural language request (which may be in English, Russian, or any other language) into a single executable {shell} command.\n"
            "Output ONLY the command. Do not use markdown backticks, explanations, or notes.\n"
            f"Request: {prompt}\n"
            "Command:"
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
        return clean_cmd, t("generated_ollama", lang=lang)
