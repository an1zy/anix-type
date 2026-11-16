# ANIX Type

[![tests](https://github.com/an1zy/anix-type/actions/workflows/tests.yml/badge.svg)](https://github.com/an1zy/anix-type/actions/workflows/tests.yml)
![python](https://img.shields.io/badge/python-3.10%2B-blue)
![license](https://img.shields.io/badge/license-MIT-green)
![dependencies](https://img.shields.io/badge/dependencies-0-brightgreen)
![status](https://img.shields.io/badge/status-active-success)

🇬🇧 English · 🇷🇺 [Русский](README.ru.md)

Context-aware shell autocompletion and command forge daemon for PowerShell and Bash. Zero dependencies, offline-first.

```powershell
# Contextual autocompletion:
PS C:\projects\anixcode> git p·ush origin main           [Tab]
PS C:\projects\anixcode> pyt·est -q                      [Tab]
PS C:\projects\anixcode> pnpm d·ev                       [Tab]

# Command forge (offline heuristics):
PS C:\projects\anixcode> ?? undo last commit keep files  [Enter]
→ git reset --soft HEAD~1

PS C:\projects\anixcode> ?? kill port 3000               [Enter]
→ Stop-Process -Id (Get-NetTCPConnection -LocalPort 3000).OwningProcess -Force

# Command forge (local model via Ollama):
PS C:\projects\anixcode> ?? top 5 memory heavy processes [Enter]
→ Get-Process | Sort-Object -Property WorkingSet -Descending | Select-Object -First 5
```

---

## Design Principles

- **Zero runtime dependencies:** Implemented entirely using Python 3 standard library (`http.server`, `urllib`, `json`).
- **Low-latency context engine:** Directly reads `.git/HEAD`, parses `package.json` scripts, and checks directory contents without spawning child shells.
- **Offline by default:** Common operations (Git branches, commits, stashes, process management, filesystem queries) are resolved deterministically on the local machine.
- **Pluggable model backends:** Supports local Ollama instances or any OpenAI-compatible API (DeepSeek, Groq, custom proxies) for arbitrary natural language translation.
- **Bilingual input:** Command forge parser handles both English and Russian queries.
- **Shell integration:** Connects to `PSReadLine` key handlers (`Tab`, `RightArrow`, `Enter`) with fallback to native tab completion.

---

## Install

Requires Python 3.10+.

```bash
pip install anix-type
```

### Hook into PowerShell

Add the integration hook to your PowerShell `$PROFILE`:

```powershell
anix-type install
```

Reload the current session:

```powershell
. $PROFILE
```

---

## Usage

### Autocompletion

Type the beginning of a command and press **Tab** or **RightArrow (→)**:

| Input | Predicted command | Context |
|---|---|---|
| `git p` + Tab | `git push origin <current-branch>` | Reads branch from `.git/HEAD` |
| `git s` + Tab | `git status` | Git repository |
| `pyt` + Tab | `pytest -q` | Python repository |
| `py` + Tab | `python` | Python environment |
| `pnpm d` + Tab | `pnpm dev` | Reads scripts from `package.json` |
| `pip i` + Tab | `pip install ` | Python |

### Command Forge (`?? <query>`)

Prefix the prompt with `??` and press **Enter**:

```powershell
# Git
?? undo last commit keep files       → git reset --soft HEAD~1
?? stash changes                     → git stash
?? pop stash                         → git stash pop
?? new branch feat-login             → git checkout -b feat-login
?? discard changes                   → git restore .

# System and processes
?? kill port 8080                    → Stop-Process -Id (Get-NetTCPConnection -LocalPort 8080).OwningProcess -Force
?? top memory processes              → Get-Process | Sort-Object -Property WorkingSet -Descending | Select-Object -First 5
?? folder size                       → calculates folder size in MB
?? find file settings.py             → Get-ChildItem -Recurse -Filter "*settings.py*"

# Python and containers
?? create venv                       → python -m venv .venv
?? activate venv                     → .\.venv\Scripts\Activate.ps1
?? purge pip cache                   → pip cache purge
?? stop all docker containers        → docker stop $(docker ps -q)
```

---

## Model Configuration (Optional)

ANIX Type does not require internet access or API keys for standard workflows. If you want model-based translation for arbitrary queries, configure a backend:

### Local Ollama

```bash
winget install Ollama.Ollama
ollama run qwen2.5-coder:1.5b
anix-type config --ollama --model qwen2.5-coder:1.5b
```

### DeepSeek / OpenAI / Custom Endpoints

```bash
anix-type config --openai-key sk-... --base-url https://api.deepseek.com/v1 --model deepseek-chat
```

### Groq

```bash
anix-type config --groq-key gsk_...
```

---

## CLI Reference

```bash
anix-type status    # Show daemon status, port, and active provider
anix-type start     # Launch daemon in background
anix-type stop      # Terminate background daemon
anix-type daemon    # Run in foreground with verbose logging
anix-type config    # Set provider and model parameters
anix-type install   # Register hook in PowerShell profile
```

---

## Architecture

```
                  ┌──────────────────────────────────────────────┐
                  │            Terminal (PSReadLine)             │
                  └───────────────┬──────────────────────────────┘
                                  │ HTTP / JSON
                                  ▼
                  ┌──────────────────────────────────────────────┐
                  │      ANIX Type Daemon (127.0.0.1:8766)       │
                  ├──────────────────────────────┬───────────────┤
                  │        Context Engine        │ History Index │
                  └───────────────┬──────────────┴───────────────┘
                                  │
                  ┌───────────────┴───────────────┐
                  ▼                               ▼
       [Deterministic Heuristics]      [Model Backend Layer]
       • Direct .git/HEAD reader       • Local Ollama (qwen2.5-coder)
       • package.json script parser    • DeepSeek / OpenAI / Groq
       • Bilingual intent patterns     • Offline fallback
```

---

## License

MIT © [an1zy](https://github.com/an1zy)
