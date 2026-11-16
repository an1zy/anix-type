"""Command-line interface for anix-type."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

from . import __version__
from .server import run_server
from .settings import Settings, get_config_dir


def _check_running(port: int = 8766) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=0.5) as resp:
            return resp.status == 200
    except Exception:
        return False


def cmd_status(args: argparse.Namespace) -> None:
    settings = Settings.load()
    running = _check_running(settings.port)
    print(f"⚡ ANIX Type v{__version__}")
    print(f"  Daemon status: {'🟢 Running' if running else '🔴 Stopped'}")
    print(f"  Port:          {settings.port}")
    print(f"  AI Provider:   {settings.ai_provider}")
    print(f"  AI Model:      {settings.model}")
    if settings.ai_provider == "groq":
        masked = (settings.groq_api_key[:6] + "…" + settings.groq_api_key[-4:]) if len(settings.groq_api_key) > 10 else "(not set)"
        print(f"  Groq Key:      {masked}")


def cmd_daemon(args: argparse.Namespace) -> None:
    run_server(port=args.port, verbose=args.verbose)


def cmd_start(args: argparse.Namespace) -> None:
    settings = Settings.load()
    if _check_running(settings.port):
        print(f"⚡ ANIX Type is already running on port {settings.port}!")
        return

    exe = sys.executable
    if sys.platform == "win32":
        pw = Path(sys.executable).parent / "pythonw.exe"
        if pw.is_file():
            exe = str(pw)

    cmd = [exe, "-m", "anix_type", "daemon", "--port", str(settings.port)]
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]

    subprocess.Popen(
        cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
        close_fds=True,
    )
    print(f"⚡ ANIX Type started in background on http://127.0.0.1:{settings.port}")


def cmd_stop(args: argparse.Namespace) -> None:
    settings = Settings.load()
    if not _check_running(settings.port):
        print("ANIX Type is not running.")
        return

    if sys.platform == "win32":
        try:
            out = subprocess.check_output(f"netstat -ano | findstr :{settings.port}", shell=True, text=True)
            for line in out.splitlines():
                if "LISTENING" in line:
                    pid = line.strip().split()[-1]
                    subprocess.run(f"taskkill /PID {pid} /F", shell=True, check=False)
                    print("⚡ ANIX Type daemon stopped.")
                    return
        except Exception:
            pass
    print("Could not automatically stop daemon. Please close the process.")


def cmd_install(args: argparse.Namespace) -> None:
    """Install integration hook into PowerShell profile or bash/zsh."""
    if sys.platform == "win32":
        _install_powershell()
    else:
        print("For Linux/macOS, add `eval $(anix-type init zsh)` to your ~/.zshrc or ~/.bashrc.")


def _get_powershell_profile_path() -> Path:
    candidates = [
        Path.home() / "Documents" / "WindowsPowerShell" / "Microsoft.PowerShell_profile.ps1",
        Path.home() / "OneDrive" / "Documents" / "WindowsPowerShell" / "Microsoft.PowerShell_profile.ps1",
    ]
    for c in candidates:
        if c.is_file():
            return c

    try:
        raw = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; Write-Output $PROFILE"],
        )
        path_str = raw.decode("utf-8", errors="replace").strip()
        if path_str:
            return Path(path_str)
    except Exception:
        pass

    return candidates[0]


def _install_powershell() -> None:
    ps_file = Path(__file__).resolve().parent / "integrations" / "anix-type.ps1"
    if not ps_file.is_file():
        print(f"Error: integration script not found at {ps_file}")
        return

    profile_path = _get_powershell_profile_path()
    profile_path.parent.mkdir(parents=True, exist_ok=True)

    hook_line = f'. "{ps_file}"'
    existing = ""
    if profile_path.is_file():
        existing = profile_path.read_text(encoding="utf-8", errors="ignore")

    if hook_line in existing:
        print("✓ ANIX Type is already hooked into your PowerShell $PROFILE:")
        print(f"  {profile_path}")
    else:
        with open(profile_path, "a", encoding="utf-8") as f:
            if existing and not existing.endswith("\n"):
                f.write("\n")
            f.write(f"\n# ANIX Type shell autocompletion\n{hook_line}\n")
        print("🎉 Successfully hooked ANIX Type into PowerShell $PROFILE:")
        print(f"  {profile_path}")
        print("\nTo activate immediately, restart PowerShell or run:")
        print(f'  . "$PROFILE"')


def cmd_config(args: argparse.Namespace) -> None:
    settings = Settings.load()
    if args.groq_key:
        settings.groq_api_key = args.groq_key.strip()
        settings.ai_provider = "groq"
        settings.save()
        print("✓ Groq API key saved and activated!")
    elif args.ollama:
        settings.ai_provider = "ollama"
        if args.model:
            settings.model = args.model
        settings.save()
        print("✓ Switched AI provider to local Ollama!")
    else:
        print("Usage:")
        print("  anix-type config --groq-key gsk_...")
        print("  anix-type config --ollama [--model qwen2.5-coder:1.5b]")


def main() -> None:
    parser = argparse.ArgumentParser(prog="anix-type", description="Context-aware AI autocompletion for terminal.")
    subparsers = parser.add_subparsers(dest="command")

    p_daemon = subparsers.add_parser("daemon", help="Run the daemon in foreground")
    p_daemon.add_argument("--port", type=int, default=8766, help="Port to listen on (default: 8766)")
    p_daemon.add_argument("--verbose", action="store_true", help="Enable debug logging")

    subparsers.add_parser("start", help="Start the daemon in background")
    subparsers.add_parser("stop", help="Stop the running background daemon")
    subparsers.add_parser("status", help="Show daemon and AI configuration status")
    subparsers.add_parser("install", help="Hook ANIX Type into PowerShell $PROFILE")

    p_conf = subparsers.add_parser("config", help="Configure AI providers and keys")
    p_conf.add_argument("--groq-key", help="Free Groq API key from console.groq.com")
    p_conf.add_argument("--ollama", action="store_true", help="Use local Ollama")
    p_conf.add_argument("--model", help="Model name")

    args = parser.parse_args()
    if not args.command:
        cmd_status(args)
        return

    commands = {
        "status": cmd_status,
        "daemon": cmd_daemon,
        "start": cmd_start,
        "stop": cmd_stop,
        "install": cmd_install,
        "config": cmd_config,
    }

    fn = commands.get(args.command)
    if fn:
        fn(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
