"""Internationalization & language detection for anix-type."""
from __future__ import annotations

import locale
import os
import sys


def detect_language() -> str:
    """Detect whether system language is Russian ('ru') or English ('en')."""
    # 1. Environment variable override
    env = (os.environ.get("ANIX_LANG") or os.environ.get("LANG") or os.environ.get("LC_ALL") or "").lower()
    if env.startswith("ru"):
        return "ru"
    if env.startswith("en"):
        return "en"

    # 2. Python locale
    try:
        loc = locale.getlocale()[0]
        if loc and loc.lower().startswith(("ru", "russian")):
            return "ru"
    except Exception:
        pass

    # 3. Windows UI culture fallback
    if sys.platform == "win32":
        try:
            import ctypes
            lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0xFF
            if lang_id == 0x19:  # Russian LANGID
                return "ru"
        except Exception:
            pass

    return "en"


MESSAGES = {
    "en": {
        "ready": "⚡ ANIX Type ready",
        "running": "🟢 Running",
        "stopped": "🔴 Stopped",
        "daemon_status": "  Daemon status: ",
        "port": "  Port:          ",
        "ai_provider": "  AI Provider:   ",
        "ai_model": "  AI Model:      ",
        "groq_key": "  Groq Key:      ",
        "openai_key": "  API Key:       ",
        "already_running": "⚡ ANIX Type is already running on port {port}!",
        "started": "⚡ ANIX Type started in background on http://127.0.0.1:{port}",
        "stopped_msg": "⚡ ANIX Type daemon stopped.",
        "not_running": "ANIX Type is not running.",
        "ai_not_configured": "AI is not configured. Set Ollama with `anix-type config --ollama` or set an API key.",
        "instant_heuristic": "Instant offline heuristic",
        "generated_ollama": "Generated via local Ollama",
        "generated_groq": "Generated via Groq",
        "generated_ai": "Generated via AI",
        "hooked_already": "✓ ANIX Type is already hooked into your PowerShell $PROFILE:",
        "hooked_success": "🎉 Successfully hooked ANIX Type into PowerShell $PROFILE:",
        "to_activate": "To activate immediately, restart PowerShell or run:\n  . \"$PROFILE\"",
    },
    "ru": {
        "ready": "⚡ ANIX Type готов к работе",
        "running": "🟢 Запущен",
        "stopped": "🔴 Остановлен",
        "daemon_status": "  Статус демона: ",
        "port": "  Порт:          ",
        "ai_provider": "  ИИ-провайдер:  ",
        "ai_model": "  Модель ИИ:     ",
        "groq_key": "  Ключ Groq:     ",
        "openai_key": "  Ключ API:      ",
        "already_running": "⚡ ANIX Type уже запущен на порту {port}!",
        "started": "⚡ ANIX Type запущен в фоне на http://127.0.0.1:{port}",
        "stopped_msg": "⚡ Демон ANIX Type остановлен.",
        "not_running": "ANIX Type не запущен.",
        "ai_not_configured": "ИИ не настроен. Настрой Ollama командой `anix-type config --ollama` или укажи ключ API.",
        "instant_heuristic": "Мгновенная оффлайн-эвристика",
        "generated_ollama": "Сгенерировано локальной Ollama",
        "generated_groq": "Сгенерировано через Groq",
        "generated_ai": "Сгенерировано нейросетью",
        "hooked_already": "✓ ANIX Type уже подключен в твой PowerShell $PROFILE:",
        "hooked_success": "🎉 ANIX Type успешно подключен в PowerShell $PROFILE:",
        "to_activate": "Чтобы применить прямо сейчас, перезапусти PowerShell или выполни:\n  . \"$PROFILE\"",
    },
}


def t(key: str, lang: str | None = None, **kwargs) -> str:
    """Get localized text string."""
    selected_lang = lang or detect_language()
    table = MESSAGES.get(selected_lang, MESSAGES["en"])
    text = table.get(key, MESSAGES["en"].get(key, key))
    if kwargs:
        text = text.format(**kwargs)
    return text
