from django.apps import AppConfig
from django.db.backends.signals import connection_created
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _


class ShopConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "shop"
    # Русская надпись группы в сайдбаре админки. Без этого Django берёт
    # default `name.title()` → «Shop». gettext_lazy — чтобы работать через
    # i18n-систему, а не хардкодом.
    verbose_name = _("Магазин")

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
