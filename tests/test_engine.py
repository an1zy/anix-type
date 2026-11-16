from pathlib import Path
from anix_type.engine.context import ProjectContext, extract_context, get_git_info, get_package_scripts
from anix_type.engine.history import HistoryIndex
from anix_type.engine.heuristics import predict_heuristics


def test_git_detection(tmp_path: Path):
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "HEAD").write_text("ref: refs/heads/feat/awesome-feature\n", encoding="utf-8")

    root, branch = get_git_info(tmp_path)
    assert root == tmp_path
    assert branch == "feat/awesome-feature"


def test_package_scripts(tmp_path: Path):
    (tmp_path / "package.json").write_text('{"scripts": {"dev": "vite", "build": "tsc"}}', encoding="utf-8")
    (tmp_path / "pnpm-lock.yaml").write_text("", encoding="utf-8")

    mgr, scripts = get_package_scripts(tmp_path)
    assert mgr == "pnpm"
    assert "dev" in scripts
    assert "build" in scripts


def test_heuristics_git():
    ctx = ProjectContext(cwd=Path.cwd(), is_git=True, git_branch="feature-x")
    sug = predict_heuristics("git p", ctx)
    assert sug is not None
    assert sug.text == "git push origin feature-x"
    assert sug.suffix == "ush origin feature-x"


def test_heuristics_package():
    ctx = ProjectContext(cwd=Path.cwd(), package_manager="pnpm", scripts=["dev", "build"])
    sug = predict_heuristics("pnpm d", ctx)
    assert sug is not None
    assert sug.text == "pnpm dev"


def test_history_frecency(tmp_path: Path):
    hist_file = tmp_path / "history.txt"
    hist_file.write_text("pytest -q\ngit status\npytest -q\npytest -q\n", encoding="utf-8")

    idx = HistoryIndex(hist_file)
    matches = idx.match("py")
    assert matches == ["pytest -q"]


def test_heuristics_history_fallback(tmp_path: Path):
    hist_file = tmp_path / "history.txt"
    hist_file.write_text("cargo test --release\n", encoding="utf-8")
    idx = HistoryIndex(hist_file)

    ctx = ProjectContext(cwd=Path.cwd())
    sug = predict_heuristics("cargo t", ctx, history=idx)
    assert sug is not None
    assert sug.text == "cargo test --release"
    assert sug.source == "history"


def test_offline_forge():
    from anix_type.engine.ai import forge_command
    cmd, _ = forge_command("откатить последний коммит но оставить файлы", shell="powershell")
    assert cmd == "git reset --soft HEAD~1"

    cmd2, _ = forge_command("убить процесс на порту 8080", shell="powershell")
    assert "Stop-Process" in cmd2 and "8080" in cmd2
