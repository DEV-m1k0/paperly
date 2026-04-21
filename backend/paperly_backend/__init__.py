# Celery — опциональный в production. Если не установлен, проект работает
# как обычный Django-сайт без фоновых задач.
try:
    from .celery import app as celery_app
    __all__ = ("celery_app",)
except ImportError:
    __all__ = ()
