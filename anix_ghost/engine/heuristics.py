"""Fast heuristic predictor (<1ms).

Combines instant project context (Git, package.json, Docker, Python)
and history ranking to produce sub-millisecond ghost completions.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .context import ProjectContext
    from .history import HistoryIndex


@dataclass
class Suggestion:
    text: str  # full predicted command
    suffix: str  # part after the current input buffer (for ghost rendering)
    source: str  # "git", "package", "python", "docker", "fs", "history"
    confidence: float  # 0.0 - 1.0


def predict_heuristics(buffer: str, context: ProjectContext, history: HistoryIndex | None = None) -> Suggestion | None:
    """Predict the next tokens for buffer based on contextual rules and history."""
    clean = buffer.strip()
    if not clean:
        return None

    # 1. Git heuristics
    if context.is_git:
        git_sug = _predict_git(buffer, context)
        if git_sug:
            return git_sug

    # 2. Package manager & script heuristics
    if context.package_manager in ("pnpm", "npm", "yarn", "bun"):
        pkg_sug = _predict_package(buffer, context)
        if pkg_sug:
            return pkg_sug

    # 3. Python heuristics
    py_sug = _predict_python(buffer, context)
    if py_sug:
        return py_sug

    # 4. Docker heuristics
    docker_sug = _predict_docker(buffer, context)
    if docker_sug:
        return docker_sug

    # 5. File / Directory navigation
    fs_sug = _predict_fs(buffer, context)
    if fs_sug:
        return fs_sug

    # 6. Fallback: Frecency-based History match
    if history:
        hist_matches = history.match(buffer, max_results=1)
        if hist_matches:
            target = hist_matches[0]
            if target.lower().startswith(buffer.lower()) and len(target) > len(buffer):
                suffix = target[len(buffer):]
                return Suggestion(text=target, suffix=suffix, source="history", confidence=0.7)

    return None


def _predict_git(buffer: str, ctx: ProjectContext) -> Suggestion | None:
    b = buffer.strip()
    branch = ctx.git_branch or "main"

    # git push
    if b in ("git p", "git pu", "git pus", "git push"):
        full = f"git push origin {branch}"
        if full.startswith(buffer):
            return Suggestion(full, full[len(buffer):], "git", 0.95)

    if b.startswith("git push ") and not b.endswith(branch):
        parts = b.split()
        if len(parts) == 2:  # 'git push '
            full = f"git push origin {branch}"
            return Suggestion(full, full[len(buffer):], "git", 0.95)

    # git pull
    if b in ("git pul", "git pull"):
        full = f"git pull origin {branch}"
        return Suggestion(full, full[len(buffer):], "git", 0.9)

    # git status
    if b in ("git s", "git st", "git sta"):
        full = "git status"
        return Suggestion(full, full[len(buffer):], "git", 0.9)

    # git checkout / switch
    if b in ("git c", "git ch", "git che", "git check", "git checkout"):
        full = f"git checkout {branch}" if branch not in ("main", "master") else "git checkout main"
        if full.startswith(buffer):
            return Suggestion(full, full[len(buffer):], "git", 0.85)

    if b in ("git checkout -b", "git checkout -b "):
        full = "git checkout -b feat/"
        return Suggestion(full, full[len(buffer):], "git", 0.8)

    # git commit
    if b in ("git com", "git comm", "git commit"):
        full = 'git commit -m "'
        return Suggestion(full, full[len(buffer):], "git", 0.9)

    if b.startswith('git commit -m "') and b == 'git commit -m "':
        full = 'git commit -m "feat: '
        return Suggestion(full, full[len(buffer):], "git", 0.8)

    # git add
    if b in ("git a", "git ad", "git add"):
        full = "git add ."
        return Suggestion(full, full[len(buffer):], "git", 0.9)

    # git diff & log
    if b in ("git d", "git di", "git dif"):
        return Suggestion("git diff", "git diff"[len(buffer):], "git", 0.9)
    if b in ("git l", "git lo"):
        return Suggestion("git log --oneline -n 10", "git log --oneline -n 10"[len(buffer):], "git", 0.9)

    return None


def _predict_package(buffer: str, ctx: ProjectContext) -> Suggestion | None:
    b = buffer.strip()
    mgr = ctx.package_manager or "npm"

    # Match npm/pnpm run <script>
    for script in ctx.scripts:
        candidates = [
            f"{mgr} run {script}",
            f"{mgr} {script}",
        ]
        for cand in candidates:
            if cand.lower().startswith(b.lower()) and len(cand) > len(buffer):
                return Suggestion(cand, cand[len(buffer):], "package", 0.9)

    # Common package commands
    if b in (f"{mgr} i", f"{mgr} in", f"{mgr} ins", f"{mgr} inst"):
        full = f"{mgr} install"
        return Suggestion(full, full[len(buffer):], "package", 0.9)

    if b in (f"{mgr} b", f"{mgr} bu"):
        full = f"{mgr} build" if "build" in ctx.scripts else f"{mgr} run build"
        return Suggestion(full, full[len(buffer):], "package", 0.85)

    if b in (f"{mgr} d", f"{mgr} de"):
        full = f"{mgr} dev" if "dev" in ctx.scripts else f"{mgr} run dev"
        return Suggestion(full, full[len(buffer):], "package", 0.85)

    return None


def _predict_python(buffer: str, ctx: ProjectContext) -> Suggestion | None:
    b = buffer.strip()

    # pytest
    if b in ("pyt", "pyte", "pyst", "pytest"):
        full = "pytest -q"
        return Suggestion(full, full[len(buffer):], "python", 0.9)

    # python <script>.py
    for py_prefix in ("python ", "py ", "python3 "):
        if buffer.startswith(py_prefix):
            typed_file = buffer[len(py_prefix):].strip()
            for filename in ctx.recent_files:
                if filename.endswith(".py") and not filename.startswith("_"):
                    if filename.lower().startswith(typed_file.lower()):
                        full = f"{py_prefix}{filename}"
                        return Suggestion(full, full[len(buffer):], "python", 0.85)

    # pip install
    if b in ("pip i", "pip in", "pip ins", "pip inst"):
        full = "pip install "
        return Suggestion(full, full[len(buffer):], "python", 0.9)

    return None


def _predict_docker(buffer: str, ctx: ProjectContext) -> Suggestion | None:
    b = buffer.strip()

    if b in ("docker c", "docker co", "docker com"):
        return Suggestion("docker compose up -d", "docker compose up -d"[len(buffer):], "docker", 0.85)

    if b in ("docker compose u", "docker compose up"):
        return Suggestion("docker compose up -d", "docker compose up -d"[len(buffer):], "docker", 0.9)

    if b in ("docker compose d", "docker compose dow"):
        return Suggestion("docker compose down", "docker compose down"[len(buffer):], "docker", 0.9)

    if b in ("docker compose l", "docker compose log"):
        service_suffix = f" {ctx.docker_services[0]}" if ctx.docker_services else ""
        full = f"docker compose logs -f{service_suffix}"
        return Suggestion(full, full[len(buffer):], "docker", 0.85)

    return None


def _predict_fs(buffer: str, ctx: ProjectContext) -> Suggestion | None:
    for cmd in ("cd ", "cat ", "type ", "code ", "vim ", "nano "):
        if buffer.startswith(cmd):
            typed_target = buffer[len(cmd):].strip()
            only_dirs = cmd == "cd "
            for filename in ctx.recent_files:
                is_dir = filename.endswith("/")
                if only_dirs and not is_dir:
                    continue
                clean_name = filename.rstrip("/")
                if clean_name.lower().startswith(typed_target.lower()):
                    full = f"{cmd}{clean_name}" + ("/" if is_dir else "")
                    return Suggestion(full, full[len(buffer):], "fs", 0.8)
    return None
