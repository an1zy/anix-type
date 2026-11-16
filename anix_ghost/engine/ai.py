"""AI Command Forge: turns natural language into exact shell commands via Groq / Ollama."""
from __future__ import annotations

import json
import urllib.request
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..settings import Settings


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
    return "", "AI is not configured yet. Run `anix-ghost config` or set your free Groq key!"


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
