# ANIX Type

[![tests](https://github.com/an1zy/anix-type/actions/workflows/tests.yml/badge.svg)](https://github.com/an1zy/anix-type/actions/workflows/tests.yml)
![python](https://img.shields.io/badge/python-3.10%2B-blue)
![license](https://img.shields.io/badge/license-MIT-green)
![dependencies](https://img.shields.io/badge/dependencies-0-brightgreen)
![status](https://img.shields.io/badge/status-active-success)

[English](README.md) · 🇷🇺 Русский

Контекстный автокомплит и кузница команд для PowerShell и Bash. Ноль внешних зависимостей, оффлайн по умолчанию.

```powershell
# Контекстный автокомплит:
PS C:\projects\anixcode> git p·ush origin main           [Tab]
PS C:\projects\anixcode> pyt·est -q                      [Tab]
PS C:\projects\anixcode> pnpm d·ev                       [Tab]

# Кузница команд (детерминированные эвристики):
PS C:\projects\anixcode> ?? откатить последний коммит но оставить файлы [Enter]
→ git reset --soft HEAD~1

PS C:\projects\anixcode> ?? прибить порт 3000                           [Enter]
→ Stop-Process -Id (Get-NetTCPConnection -LocalPort 3000).OwningProcess -Force

# Кузница команд (локальная модель через Ollama):
PS C:\projects\anixcode> ?? покажи топ 5 процессов по памяти            [Enter]
→ Get-Process | Sort-Object -Property WorkingSet -Descending | Select-Object -First 5
```

---

## Принципы разработки

- **Ноль внешних зависимостей:** написан исключительно на стандартной библиотеке Python 3 (`http.server`, `urllib`, `json`).
- **Низкие задержки контекста:** напрямую читает `.git/HEAD`, парсит скрипты `package.json` и проверяет файлы без запуска дочерних процессов оболочки.
- **Оффлайн по умолчанию:** типовые задачи (ветки, коммиты, стэш, остановка процессов, поиск файлов) разрешаются локально без обращений к сети.
- **Подключаемые бэкенды моделей:** поддерживает локальную Ollama или любой OpenAI-совместимый API (DeepSeek, Groq, собственные прокси) для произвольных запросов.
- **Двуязычный парсер:** кузница команд `??` принимает запросы на русском и английском языках.
- **Интеграция с оболочкой:** встраивается в обработчики клавиш `PSReadLine` (`Tab`, `RightArrow`, `Enter`) с автоматическим откатом на нативный автокомплит.

---

## Установка

Требуется Python 3.10+.

```bash
pip install anix-type
```

### Подключение к PowerShell

Запусти установщик хука в профиль `$PROFILE`:

```powershell
anix-type install
```

Перезагрузи сессию:

```powershell
. $PROFILE
```

---

## Использование

### Автокомплит

Набирай начало команды и нажимай **Tab** или **Стрелку вправо (→)**:

| Ввод | Дополнение ANIX Type | Контекст |
|---|---|---|
| `git p` + Tab | `git push origin <ветка>` | Читает текущую ветку из `.git/HEAD` |
| `git s` + Tab | `git status` | Репозиторий Git |
| `pyt` + Tab | `pytest -q` | Репозиторий Python |
| `py` + Tab | `python` | Окружение Python |
| `pnpm d` + Tab | `pnpm dev` | Читает скрипты из `package.json` |
| `pip i` + Tab | `pip install ` | Python |

### Кузница команд (`?? <запрос>`)

Набирай `??` и текст запроса, затем нажимай **Enter**:

```powershell
# Git
?? откатить последний коммит но оставить файлы → git reset --soft HEAD~1
?? спрятать изменения                          → git stash
?? вернуть изменения                           → git stash pop
?? создать ветку feat-login                    → git checkout -b feat-login
?? сбросить все изменения                      → git restore .

# Система и процессы
?? прибить порт 8080                           → Stop-Process -Id (Get-NetTCPConnection -LocalPort 8080).OwningProcess -Force
?? покажи 5 процессов жрущих больше всего ram  → Get-Process | Sort-Object -Property WorkingSet -Descending | Select-Object -First 5
?? размер папки                                → подсчитывает размер в МБ
?? найти файл settings.py                      → Get-ChildItem -Recurse -Filter "*settings.py*"

# Python и контейнеры
?? создать окружение venv                      → python -m venv .venv
?? активировать venv                           → .\.venv\Scripts\Activate.ps1
?? очистить кэш pip                            → pip cache purge
?? остановить все контейнеры docker            → docker stop $(docker ps -q)
```

---

## Настройка моделей (Опционально)

Для работы ANIX Type не требуется интернет или API ключи. Если нужна нейросетевая трансляция для нестандартных задач:

### Локальная Ollama

```bash
winget install Ollama.Ollama
ollama run qwen2.5-coder:1.5b
anix-type config --ollama --model qwen2.5-coder:1.5b
```

### DeepSeek / OpenAI / Собственный прокси

```bash
anix-type config --openai-key sk-... --base-url https://api.deepseek.com/v1 --model deepseek-chat
```

### Groq

```bash
anix-type config --groq-key gsk_...
```

---

## Справочник CLI

```bash
anix-type status    # Показать статус демона, порт и активный бэкенд
anix-type start     # Запустить фоновый демон
anix-type stop      # Остановить фоновый демон
anix-type daemon    # Запустить в терминале с подробными логами
anix-type config    # Настроить провайдера и модель
anix-type install   # Прописать хук в профиль PowerShell
```

---

## Лицензия

MIT © [an1zy](https://github.com/an1zy)
