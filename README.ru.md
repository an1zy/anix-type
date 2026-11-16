# ANIX Type

[![tests](https://github.com/an1zy/anix-type/actions/workflows/tests.yml/badge.svg)](https://github.com/an1zy/anix-type/actions/workflows/tests.yml)
![python](https://img.shields.io/badge/python-3.10%2B-blue)
![license](https://img.shields.io/badge/license-MIT-green)
![dependencies](https://img.shields.io/badge/dependencies-0-brightgreen)
![status](https://img.shields.io/badge/status-active-success)

[English](README.md) · 🇷🇺 Русский

> Контекстный автокомплит и кузница команд на естественном языке для твоего терминала. Ноль внешних зависимостей. Задержка менее 1 мс. Работает 100% оффлайн.

```powershell
# 1. Мгновенный эвристический автокомплит (<0.05 мс):
PS C:\projects\anixcode> git p·ush origin main           [Tab]
PS C:\projects\anixcode> pyt·est -q                      [Tab]
PS C:\projects\anixcode> pnpm d·ev                       [Tab]

# 2. Кузница команд на обычном русском языке:
PS C:\projects\anixcode> ?? откатить последний коммит но оставить файлы [Enter]
→ git reset --soft HEAD~1

PS C:\projects\anixcode> ?? прибить порт 3000                           [Enter]
→ Stop-Process -Id (Get-NetTCPConnection -LocalPort 3000).OwningProcess -Force

# 3. Безлимитный локальный ИИ через Ollama (qwen2.5-coder:1.5b):
PS C:\projects\anixcode> ?? покажи топ 5 процессов по памяти            [Enter]
→ Get-Process | Sort-Object -Property WorkingSet -Descending | Select-Object -First 5
```

---

## Почему ANIX Type?

- **⚡ Ноль внешних зависимостей:** Написан строго на стандартной библиотеке Python 3 (`http.server`, `urllib`, `json`). Ставится мгновенно, никаких конфликтов пакетов.
- **⚡ Сверхбыстрый контекстный движок:** Напрямую читает `.git/HEAD` (<0.05 мс), парсит скрипты из `package.json`, определяет виртуальные окружения Python и Docker на лету.
- **🔒 100% оффлайн и приватность:** Встроенный эвристический движок закрывает 95% повседневных команд локально, вообще не отправляя ничего в сеть.
- **🧠 Безлимитный ИИ прямо на ПК:** Подключается к локальной [Ollama](https://ollama.com) (`qwen2.5-coder:1.5b`) для полной оффлайн-работы без блокировок и VPN, либо к любому OpenAI-совместимому API (DeepSeek, Groq, OpenAI).
- **🌍 Двуязычный (RU + EN):** Понимает запросы на русском и английском языках из коробки.
- **💻 Нативная интеграция с PowerShell:** Чисто подключается к `PSReadLine` для мгновенной работы клавиш `Tab`, `Стрелка вправо` и `Enter` без мерцания строки.

---

## Установка

Требуется Python 3.10+.

```bash
pip install anix-type
```

### 1. Подключение к PowerShell

Выполни команду установки один раз, чтобы добавить хук в профиль `$PROFILE`:

```powershell
anix-type install
```

Перезагрузи текущую сессию терминала:

```powershell
. $PROFILE
```

*(В консоли загорится плашка `⚡ ANIX Type ready`)*.

---

## Использование

### Мгновенный автокомплит

Набирай первые буквы и нажимай **Tab** или **Стрелку вправо (→)**:

| Что набираешь | Что подставит ANIX Type | Контекст |
|---|---|---|
| `git p` + Tab | `git push origin <твоя-ветка>` | Читает реальную ветку из `.git/HEAD` |
| `git s` + Tab | `git status` | Репозиторий Git |
| `pyt` + Tab | `pytest -q` | Проект Python |
| `py` + Tab | `python` | Среда Python |
| `pnpm d` + Tab | `pnpm dev` | Читает скрипты из `package.json` |
| `pip i` + Tab | `pip install ` | Python |

### Кузница команд (`?? <что ты хочешь сделать>`)

Набирай `??` и свой запрос обычным языком, затем нажимай **Enter**:

```powershell
# Работа с Git
?? откатить последний коммит но оставить файлы → git reset --soft HEAD~1
?? спрятать изменения                          → git stash
?? вернуть изменения                           → git stash pop
?? создать ветку feat-login                    → git checkout -b feat-login
?? сбросить все изменения                      → git restore .

# Система и порты
?? прибить порт 8080                           → Stop-Process -Id (Get-NetTCPConnection -LocalPort 8080).OwningProcess -Force
?? покажи 5 процессов жрущих больше всего ram  → Get-Process | Sort-Object -Property WorkingSet -Descending | Select-Object -First 5
?? размер папки                                → подсчитывает размер в МБ
?? найти файл settings.py                      → Get-ChildItem -Recurse -Filter "*settings.py*"

# Python и Docker
?? создать окружение venv                      → python -m venv .venv
?? активировать venv                           → .\.venv\Scripts\Activate.ps1
?? очистить кэш pip                            → pip cache purge
?? остановить все контейнеры docker            → docker stop $(docker ps -q)
```

---

## ИИ-провайдеры (Опционально)

ANIX Type работает полностью оффлайн на шаблонах. Для сложных нестандартных запросов можно подключить ИИ:

### 1. Локальная Ollama (Рекомендуется — 100% Бесплатно и Оффлайн)

```bash
# Установить Ollama и скачать легкую модель для кода
winget install Ollama.Ollama
ollama run qwen2.5-coder:1.5b

# Переключить ANIX Type на Ollama
anix-type config --ollama --model qwen2.5-coder:1.5b
```

### 2. DeepSeek / OpenAI / Любой прокси

```bash
anix-type config --openai-key sk-... --base-url https://api.deepseek.com/v1 --model deepseek-chat
```

### 3. Groq (Облачный сверхбыстрый API)

```bash
anix-type config --groq-key gsk_...
```

---

## Команды CLI

```bash
anix-type status    # Проверить статус демона, порт и провайдер ИИ
anix-type start     # Запустить демон в фоне (автозапуск при открытии терминала)
anix-type stop      # Остановить фоновый демон
anix-type daemon    # Запустить в терминале с логами --verbose
anix-type config    # Настроить модель ИИ и ключи API
anix-type install   # Подключить хук в профиль PowerShell
```

---

## Лицензия

MIT © [an1zy](https://github.com/an1zy)
