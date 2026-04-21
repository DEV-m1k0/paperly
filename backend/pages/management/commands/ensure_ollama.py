"""
Ensure the local Ollama daemon is running and the configured model is pulled.

Uses Ollama's REST API for pulling models (works even when the `ollama` CLI
isn't on PATH — common on Windows where Ollama installs as a background
service only). Falls back to spawning `ollama serve` via the CLI if the
daemon isn't reachable and the CLI *is* available.

Called automatically by our custom `runserver` before the dev server starts.
Can also be run standalone:

    python manage.py ensure_ollama           # start daemon + pull model
    python manage.py ensure_ollama --check   # check only, exit 1 if not ready
"""

from __future__ import annotations

import json
import platform
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


DAEMON_URL = "http://localhost:11434"
STARTUP_TIMEOUT_SEC = 30
PULL_TIMEOUT_SEC = 60 * 30  # model pulls can take a while on slow internet
OLLAMA_INSTALL_URL = "https://ollama.com/download"


def _daemon_reachable(timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(f"{DAEMON_URL}/api/tags", timeout=timeout) as resp:
            return resp.status == 200
    except (urllib.error.URLError, OSError):
        return False


def _list_pulled_models() -> set[str]:
    try:
        with urllib.request.urlopen(f"{DAEMON_URL}/api/tags", timeout=5) as resp:
            data = json.loads(resp.read())
    except Exception:
        return set()
    return {m.get("name", "") for m in data.get("models", []) if m.get("name")}


def _points_at_ollama(base_url: str) -> bool:
    base = (base_url or "").lower()
    return "localhost:11434" in base or "127.0.0.1:11434" in base


def _start_daemon_via_cli() -> subprocess.Popen | None:
    ollama = shutil.which("ollama")
    if not ollama:
        return None
    popen_kwargs: dict = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "stdin": subprocess.DEVNULL,
    }
    if platform.system() == "Windows":
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | getattr(subprocess, "DETACHED_PROCESS", 0)
        popen_kwargs["creationflags"] = flags
    else:
        popen_kwargs["start_new_session"] = True
    return subprocess.Popen([ollama, "serve"], **popen_kwargs)


def _wait_for_daemon(timeout: float = STARTUP_TIMEOUT_SEC) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _daemon_reachable():
            return True
        time.sleep(0.5)
    return False


def _model_is_pulled(model: str, pulled: set[str]) -> bool:
    # Exact match (including the `:tag` suffix) — strict by design: if user
    # asks for llama3.2:3b, having only llama3.2:1b should trigger a pull.
    if model in pulled:
        return True
    # Also accept the un-tagged form: asking for "llama3.2" matches "llama3.2:latest".
    if ":" not in model:
        return any(m == f"{model}:latest" for m in pulled)
    return False


def _pull_via_rest(model: str, stdout) -> bool:
    """Stream Ollama's /api/pull endpoint. Returns True on success."""
    body = json.dumps({"model": model, "stream": True}).encode()
    req = urllib.request.Request(
        f"{DAEMON_URL}/api/pull",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    last_status = ""
    try:
        with urllib.request.urlopen(req, timeout=PULL_TIMEOUT_SEC) as resp:
            for raw_line in resp:
                try:
                    event = json.loads(raw_line.decode("utf-8").strip())
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
                if event.get("error"):
                    stdout.write(f"    ! {event['error']}\n")
                    return False
                status = event.get("status", "")
                total = event.get("total")
                completed = event.get("completed")
                if status and status != last_status:
                    last_status = status
                    if total and completed is not None:
                        pct = (completed / total) * 100 if total else 0
                        stdout.write(f"    {status} — {pct:.1f}%\n")
                    else:
                        stdout.write(f"    {status}\n")
                    stdout.flush()
            return True
    except urllib.error.HTTPError as exc:
        stdout.write(f"    ! HTTP {exc.code}: {exc.read().decode('utf-8', 'replace')[:200]}\n")
        return False
    except (urllib.error.URLError, OSError) as exc:
        stdout.write(f"    ! network error: {exc}\n")
        return False


class Command(BaseCommand):
    help = "Ensure the local Ollama daemon is running and the configured model is available."

    def add_arguments(self, parser):
        parser.add_argument(
            "--check",
            action="store_true",
            help="Only check readiness. Exit 1 if daemon or model is missing.",
        )

    def handle(self, *args, **options):
        api_base = getattr(settings, "AI_API_BASE", "") or ""
        if not _points_at_ollama(api_base):
            self.stdout.write(self.style.WARNING(
                f"[ollama] AI_API_BASE={api_base!r} — not pointing at Ollama, skipping."
            ))
            return

        model = getattr(settings, "AI_MODEL", "llama3.2:3b")
        check_only = options["check"]

        # 1. Make sure the daemon is reachable.
        if _daemon_reachable():
            self.stdout.write(self.style.SUCCESS("[ollama] daemon: running"))
        else:
            if check_only:
                self.stderr.write(self.style.ERROR("[ollama] daemon is not running"))
                sys.exit(1)

            # Try to start it via CLI if available; otherwise ask the user to do it.
            if not shutil.which("ollama"):
                raise CommandError(
                    "Ollama daemon is not running and the `ollama` CLI is not on PATH.\n"
                    f"  1. Install Ollama from {OLLAMA_INSTALL_URL}\n"
                    "  2. Launch the Ollama app (it'll start the background daemon)\n"
                    "  3. Restart this shell and re-run `manage.py runserver`"
                )
            self.stdout.write("[ollama] starting `ollama serve`...")
            if _start_daemon_via_cli() is None:
                raise CommandError("Failed to spawn `ollama serve`.")
            if not _wait_for_daemon():
                raise CommandError(
                    f"Ollama daemon did not become ready within {STARTUP_TIMEOUT_SEC}s.\n"
                    "Try running `ollama serve` manually in a separate terminal."
                )
            self.stdout.write(self.style.SUCCESS("[ollama] daemon: started"))

        # 2. Make sure the model is pulled.
        pulled = _list_pulled_models()
        if _model_is_pulled(model, pulled):
            self.stdout.write(self.style.SUCCESS(f"[ollama] model `{model}`: ready"))
            return

        if check_only:
            self.stderr.write(self.style.ERROR(f"[ollama] model `{model}` is not pulled"))
            sys.exit(1)

        self.stdout.write(
            f"[ollama] pulling `{model}` — this may take several minutes the first time..."
        )
        self.stdout.flush()
        if not _pull_via_rest(model, self.stdout):
            raise CommandError(
                f"Failed to pull `{model}`. You can retry manually with:\n"
                f"  curl -X POST http://localhost:11434/api/pull -d '{{\"model\":\"{model}\"}}'"
            )
        self.stdout.write(self.style.SUCCESS(f"[ollama] model `{model}`: pulled"))
