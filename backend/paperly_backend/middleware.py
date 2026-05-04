"""Кастомные middleware для Paperly.

MediaWhiteNoiseMiddleware — расширяет WhiteNoise чтобы он раздавал не только
static, но и media. На Render (без nginx) это единственный способ отдать
загруженные через админку картинки в production.
"""
from django.conf import settings
from whitenoise.middleware import WhiteNoiseMiddleware


class MediaWhiteNoiseMiddleware(WhiteNoiseMiddleware):
    """WhiteNoise + media.

    По умолчанию WhiteNoise отдаёт только `STATIC_ROOT` под префиксом `/static/`.
    Мы добавляем `MEDIA_ROOT` под префиксом `/media/`, чтобы все закоммиченные
    в репо демо-картинки (products/, blog/, categories/, brands/) раздавались
    тем же воркером без nginx.

    Файлы индексируются один раз при старте воркера. Если в админке
    загрузят новое — оно будет 404 до перезапуска сервиса. Для демо-сайта
    на Render free tier это приемлемо: сервис и так перезапускается
    автоматически после 15 мин неактивности.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if settings.MEDIA_ROOT and settings.MEDIA_URL and not getattr(settings, "USE_S3_MEDIA", False):
            # add_files принимает путь+префикс, сканирует файлы синхронно
            self.add_files(str(settings.MEDIA_ROOT), prefix=settings.MEDIA_URL)
