"""
Dev server that auto-starts the local Ollama daemon + configured model before
the Django server comes up. Drop-in replacement for Django's built-in
`runserver` — all standard flags and behaviour are inherited.
"""

from __future__ import annotations

import os

from django.core.management import call_command
from django.core.management.commands.runserver import Command as RunserverCommand


class Command(RunserverCommand):
    def inner_run(self, *args, **options):
        # `inner_run` runs in the child process of the autoreloader (RUN_MAIN),
        # so Ollama is ensured exactly once per server start. Failures are
        # non-fatal: Django still boots so you can at least serve pages.
        if os.environ.get("RUN_MAIN") == "true" or not options.get("use_reloader", True):
            try:
                call_command("ensure_ollama")
            except SystemExit:
                raise
            except Exception as exc:
                self.stdout.write(self.style.WARNING(
                    f"[ensure_ollama] failed: {exc}\n"
                    "Django will start anyway, but /api/chat/ will return errors "
                    "until Ollama is running."
                ))
        super().inner_run(*args, **options)
