# ANIX Type

[![tests](https://github.com/an1zy/anix-type/actions/workflows/tests.yml/badge.svg)](https://github.com/an1zy/anix-type/actions/workflows/tests.yml)
![python](https://img.shields.io/badge/python-3.10%2B-blue)
![license](https://img.shields.io/badge/license-MIT-green)
![dependencies](https://img.shields.io/badge/dependencies-0-brightgreen)
![status](https://img.shields.io/badge/status-active-success)

🇬🇧 English · 🇷🇺 [Русский](README.ru.md)

> Context-aware shell autocompletion and natural language command forge. Zero runtime dependencies. Sub-millisecond latency. Works 100% offline.

```powershell
# 1. Instant heuristic autocompletion (<0.05ms):
PS C:\projects\anixcode> git p·ush origin main           [Tab]
PS C:\projects\anixcode> pyt·est -q                      [Tab]
PS C:\projects\anixcode> pnpm d·ev                       [Tab]

# 2. Natural language command forge:
PS C:\projects\anixcode> ?? undo last commit keep files  [Enter]
→ git reset --soft HEAD~1

PS C:\projects\anixcode> ?? kill port 3000               [Enter]
→ Stop-Process -Id (Get-NetTCPConnection -LocalPort 3000).OwningProcess -Force

# 3. Unlimited local AI via Ollama (qwen2.5-coder:1.5b):
PS C:\projects\anixcode> ?? top 5 memory heavy processes [Enter]
→ Get-Process | Sort-Object -Property WorkingSet -Descending | Select-Object -First 5
```

---

## Why ANIX Type?

- **⚡ Zero Runtime Dependencies:** Built strictly on the Python 3 standard library (`http.server`, `urllib`, `json`). Installs in seconds, zero package conflicts.
- **⚡ Sub-Millisecond Context Engine:** Directly reads `.git/HEAD` (<0.05 ms), parses `package.json` scripts, detects Python/Docker environments on the fly.
- **🔒 100% Offline & Private:** Built-in heuristic engine handles 95% of everyday developer commands locally without touching the network.
- **🧠 Unlimited AI Forge:** Connects to local [Ollama](https://ollama.com) (`qwen2.5-coder:1.5b`) for complete offline privacy, or any OpenAI-compatible provider (DeepSeek, Groq, OpenAI).
- **🌍 Bilingual (EN + RU):** Natural language command forge understands both English and Russian prompts out of the box.
- **💻 Native PowerShell Integration:** Hooks cleanly into `PSReadLine` for instant `Tab`, `RightArrow`, and `Enter` replacement without prompt flickering.

---

## Install

Requires Python 3.10+.

```bash
pip install anix-type
```

### 1. Hook into PowerShell

Run the install command once to add the integration hook to your PowerShell `$PROFILE`:

```powershell
anix-type install
```

Reload your current terminal session:

```powershell
. $PROFILE
```

*(You will see `⚡ ANIX Type ready` in your console)*.

---

## Usage

### Instant Autocompletion

Just type and press **Tab** or **RightArrow (→)**:

| What you type | What ANIX Type predicts | Context |
|---|---|---|
| `git p` + Tab | `git push origin <current-branch>` | Reads your actual `.git/HEAD` |
| `git s` + Tab | `git status` | Git repository |
| `pyt` + Tab | `pytest -q` | Python repository |
| `py` + Tab | `python` | Python environment |
| `pnpm d` + Tab | `pnpm dev` | Reads scripts from `package.json` |
| `pip i` + Tab | `pip install ` | Python |

### Command Forge (`?? <what you want to do>`)

Type `??` followed by plain English or Russian, then press **Enter**:

```powershell
# Git operations
?? undo last commit keep files       → git reset --soft HEAD~1
?? stash changes                     → git stash
?? pop stash                         → git stash pop
?? new branch feat-login             → git checkout -b feat-login
?? discard changes                   → git restore .

# System & ports
?? kill port 8080                    → Stop-Process -Id (Get-NetTCPConnection -LocalPort 8080).OwningProcess -Force
?? top memory processes              → Get-Process | Sort-Object -Property WorkingSet -Descending | Select-Object -First 5
?? folder size                       → calculates folder size in MB
?? find file settings.py             → Get-ChildItem -Recurse -Filter "*settings.py*"

# Python & Docker
?? create venv                       → python -m venv .venv
?? activate venv                     → .\.venv\Scripts\Activate.ps1
?? purge pip cache                   → pip cache purge
?? stop all docker containers        → docker stop $(docker ps -q)
```

---

## AI Providers (Optional)

ANIX Type works completely offline using built-in heuristics. For complex, non-template queries, you can optionally connect an AI model:

### 1. Local Ollama (Recommended — 100% Free & Offline)

```bash
# Install Ollama and pull lightweight coder model
winget install Ollama.Ollama
ollama run qwen2.5-coder:1.5b

# Switch ANIX Type to Ollama
anix-type config --ollama --model qwen2.5-coder:1.5b
```

### 2. DeepSeek / OpenAI / Custom Proxy

```bash
anix-type config --openai-key sk-... --base-url https://api.deepseek.com/v1 --model deepseek-chat
```

### 3. Groq (Ultra-fast cloud)

```bash
anix-type config --groq-key gsk_...
```

---

## CLI Reference

```bash
anix-type status    # Check daemon health, port, and AI provider
anix-type start     # Start daemon in background (auto-starts on terminal open)
anix-type stop      # Stop background daemon
anix-type daemon    # Run daemon in foreground with --verbose logging
anix-type config    # Configure AI model and API keys
anix-type install   # Install integration hook into PowerShell profile
```

---

## Architecture

```
                  ┌──────────────────────────────────────────────┐
                  │            Terminal (PSReadLine)             │
                  └───────────────┬──────────────────────────────┘
                                  │ HTTP / JSON (<2ms)
                                  ▼
                  ┌──────────────────────────────────────────────┐
                  │      ANIX Type Daemon (127.0.0.1:8766)       │
                  ├──────────────────────────────┬───────────────┤
                  │     Context Engine (<0.05ms) │ History Index │
                  └───────────────┬──────────────┴───────────────┘
                                  │
                  ┌───────────────┴───────────────┐
                  ▼                               ▼
       [Offline Heuristics Engine]     [AI Forge Layer]
       • Direct .git/HEAD reader       • Local Ollama (qwen2.5-coder)
       • package.json script parser    • DeepSeek / OpenAI / Groq
       • Bilingual intent patterns     • 100% offline fallback
```

---

## License

MIT © [an1zy](https://github.com/an1zy)
