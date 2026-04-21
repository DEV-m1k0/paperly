from django.apps import AppConfig
from django.db.backends.signals import connection_created
from django.dispatch import receiver


class ShopConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "shop"

    def ready(self) -> None:
        from . import signals  # noqa: F401


@receiver(connection_created)
def _patch_sqlite_unicode(sender, connection, **kwargs):
    """SQLite's built-in LOWER/UPPER are ASCII-only. Register Python's str
    methods so that Lower('Блокнот') actually yields 'блокнот' — otherwise
    case-insensitive search breaks for Cyrillic text."""
    if connection.vendor != "sqlite":
        return
    connection.connection.create_function("LOWER", 1, lambda v: v.lower() if isinstance(v, str) else v, deterministic=True)
    connection.connection.create_function("UPPER", 1, lambda v: v.upper() if isinstance(v, str) else v, deterministic=True)
