"""
Admin-only HTTP endpoints для markdown-редактора.

- POST /admin/blog/upload-image/  — drag-n-drop загрузка картинок
- POST /admin/blog/preview/       — рендер markdown → HTML для live-preview

Защищены `staff_member_required`. Все ответы — JSON.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.core.files.storage import default_storage
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST

from .markdown_utils import render_markdown


# Разрешённые типы картинок и лимит размера (5 МБ).
_ALLOWED_CONTENT_TYPES = {
    "image/jpeg", "image/png", "image/webp", "image/gif",
}
_MAX_BYTES = 5 * 1024 * 1024


@staff_member_required
@require_POST
def upload_image(request):
    """Принимает multipart/form-data с полем `image`.

    Сохраняет в media/blog/inline/{YYYY-MM}/{uuid}.{ext}.
    Возвращает {"url": "/media/blog/inline/.../<file>", "name": "..."}.
    Имя файла генерится через uuid4 — гарантия уникальности
    и защита от сюрпризов с кириллицей в исходных именах.
    """
    file = request.FILES.get("image")
    if not file:
        return HttpResponseBadRequest("missing 'image' field")

    if file.size > _MAX_BYTES:
        return JsonResponse(
            {"error": f"file too large (max {_MAX_BYTES // 1024 // 1024} MB)"},
            status=400,
        )

    if file.content_type not in _ALLOWED_CONTENT_TYPES:
        return JsonResponse(
            {"error": f"unsupported type {file.content_type}"},
            status=400,
        )

    ext = os.path.splitext(file.name)[1].lower() or ".jpg"
    if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        ext = ".jpg"

    folder = datetime.now().strftime("blog/inline/%Y-%m")
    fname = f"{uuid.uuid4().hex}{ext}"
    rel = f"{folder}/{fname}"
    saved = default_storage.save(rel, file)
    url = default_storage.url(saved)
    return JsonResponse({"url": url, "name": file.name})


@staff_member_required
@require_POST
def preview(request):
    """Рендер markdown → HTML для side-by-side preview в админке.

    Принимает application/x-www-form-urlencoded с полем `text`.
    Используем тот же render_markdown, что и фронт — preview гарантирует
    1:1 соответствие итоговому виду.
    """
    text = request.POST.get("text", "")
    html = render_markdown(text)
    return JsonResponse({"html": html})
