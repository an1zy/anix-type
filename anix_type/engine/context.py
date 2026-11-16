"""Instant project context extraction (cwd, git repo, branch, package.json, docker-compose).

All operations are designed to run in <1ms without spawning heavy subprocesses whenever possible.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ProjectContext:
    cwd: Path
    is_git: bool = False
    git_root: Path | None = None
    git_branch: str | None = None
    package_manager: str | None = None  # pnpm, npm, yarn, bun, pip, cargo
    scripts: list[str] = field(default_factory=list)  # package.json scripts or Makefile targets
    docker_services: list[str] = field(default_factory=list)
    recent_files: list[str] = field(default_factory=list)  # filenames in cwd sorted by mtime


def get_git_info(start_dir: Path) -> tuple[Path | None, str | None]:
    """Fast git root and current branch detector without running `git.exe` (<0.2ms)."""
    current = start_dir.resolve()
    for directory in [current, *current.parents]:
        git_dir = directory / ".git"
        if git_dir.is_dir():
            head_file = git_dir / "HEAD"
            branch = None
            if head_file.is_file():
                try:
                    head_content = head_file.read_text(encoding="utf-8", errors="ignore").strip()
                    if head_content.startswith("ref: refs/heads/"):
                        branch = head_content[len("ref: refs/heads/"):]
                    elif head_content:
                        branch = head_content[:8]  # detached HEAD hash
                except OSError:
                    pass
            return directory, branch
        elif git_dir.is_file():
            # git worktree / submodule
            try:
                line = git_dir.read_text(encoding="utf-8", errors="ignore").strip()
                if line.startswith("gitdir:"):
                    real_git_dir = Path(line.split("gitdir:", 1)[1].strip())
                    if not real_git_dir.is_absolute():
                        real_git_dir = (directory / real_git_dir).resolve()
                    head_file = real_git_dir / "HEAD"
                    if head_file.is_file():
                        head_content = head_file.read_text(encoding="utf-8", errors="ignore").strip()
                        branch = head_content.split("/")[-1] if "refs/heads/" in head_content else head_content[:8]
                        return directory, branch
            except OSError:
                pass
    return None, None


def get_package_scripts(project_dir: Path) -> tuple[str | None, list[str]]:
    """Detect package manager and npm/pnpm scripts from package.json."""
    pkg_json = project_dir / "package.json"
    scripts: list[str] = []
    manager: str | None = None

    if (project_dir / "pnpm-lock.yaml").is_file():
        manager = "pnpm"
    elif (project_dir / "bun.lockb").is_file() or (project_dir / "bun.lock").is_file():
        manager = "bun"
    elif (project_dir / "yarn.lock").is_file():
        manager = "yarn"
    elif (project_dir / "package-lock.json").is_file():
        manager = "npm"

    if pkg_json.is_file():
        if not manager:
            manager = "npm"
        try:
            data = json.loads(pkg_json.read_text(encoding="utf-8", errors="ignore"))
            if isinstance(data, dict):
                raw_scripts = data.get("scripts", {})
                if isinstance(raw_scripts, dict):
                    scripts = list(raw_scripts.keys())
        except (OSError, json.JSONDecodeError):
            pass

    return manager, scripts


def get_docker_services(project_dir: Path) -> list[str]:
    """Quickly extract service names from docker-compose.yml or compose.yaml."""
    for filename in ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"):
        compose_file = project_dir / filename
        if compose_file.is_file():
            try:
                # Lightweight line-based parse to avoid heavy PyYAML dependency
                services: list[str] = []
                in_services = False
                for line in compose_file.read_text(encoding="utf-8", errors="ignore").splitlines():
                    stripped = line.strip()
                    if stripped.startswith("#") or not stripped:
                        continue
                    if line.startswith("services:"):
                        in_services = True
                        continue
                    if in_services:
                        if line.startswith(" ") or line.startswith("\t"):
                            indent = len(line) - len(line.lstrip())
                            if indent in (2, 4) and stripped.endswith(":"):
                                s_name = stripped[:-1].strip("\"'")
                                if s_name and not s_name.startswith("#"):
                                    services.append(s_name)
                        else:
                            break  # out of services block
                return services
            except OSError:
                pass
    return []


def get_recent_files(cwd: Path, max_files: int = 30) -> list[str]:
    """Get non-hidden filenames in cwd sorted by recent modification time."""
    try:
        entries = []
        for entry in cwd.iterdir():
            if entry.name.startswith((".", "$", "__")):
                continue
            try:
                entries.append((entry.stat().st_mtime, entry.name + ("/" if entry.is_dir() else "")))
            except OSError:
                continue
        entries.sort(key=lambda x: x[0], reverse=True)
        return [name for _, name in entries[:max_files]]
    except OSError:
        return []


def extract_context(cwd_path: str | Path | None = None) -> ProjectContext:
    """Fast snapshot of the current environment (<1ms)."""
    cwd = Path(cwd_path or Path.cwd()).resolve()
    git_root, git_branch = get_git_info(cwd)
    pkg_mgr, scripts = get_package_scripts(cwd)
    docker_services = get_docker_services(cwd)
    recent_files = get_recent_files(cwd)

    if not pkg_mgr:
        if (cwd / "pyproject.toml").is_file() or (cwd / "requirements.txt").is_file():
            pkg_mgr = "pip"
        elif (cwd / "Cargo.toml").is_file():
            pkg_mgr = "cargo"

    return ProjectContext(
        cwd=cwd,
        is_git=git_root is not None,
        git_root=git_root,
        git_branch=git_branch,
        package_manager=pkg_mgr,
        scripts=scripts,
        docker_services=docker_services,
        recent_files=recent_files,
    )
