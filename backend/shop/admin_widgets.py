"""
Markdown-редактор для Django admin.

Подключаем EasyMDE с CDN. Виджет добавляет:
- Полный тулбар: B/I/H1-H3, списки, цитаты, ссылки, картинки, таблицы,
  код, callout-кнопки, video-эмбеды, fullscreen, side-by-side preview.
- Drag-n-drop загрузку картинок: отправляет файл на
  `admin/blog/upload-image/`, получает URL и вставляет markdown
  `![alt](url)` в позицию курсора.
- Live-preview через render через бэкенд (точное соответствие тому,
  как статья будет отрисована на сайте). Запрос идёт на
  `admin/blog/preview/`.
"""
from django import forms
from django.utils.safestring import mark_safe


class MarkdownEditorWidget(forms.Textarea):
    """Textarea с подключённым EasyMDE.

    Все ассеты грузим с CDN — не тащим vendor в репозиторий.
    Если CDN недоступен (offline-разработка), редактор просто
    деградирует до обычной textarea — данные не теряются.
    """

    class Media:
        css = {
            "all": (
                "https://cdn.jsdelivr.net/npm/easymde@2.18.0/dist/easymde.min.css",
                "css/admin-markdown-editor.css",
            ),
        }
        js = (
            "https://cdn.jsdelivr.net/npm/easymde@2.18.0/dist/easymde.min.js",
            "js/admin-markdown-editor.js",
        )

    def __init__(self, attrs=None):
        default_attrs = {"class": "markdown-editor", "rows": 25}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)

    def render(self, name, value, attrs=None, renderer=None):
        textarea_html = super().render(name, value, attrs, renderer)
        # Скрытые data-атрибуты на враппере → их потом читает JS
        # для конфигурации EasyMDE по полям textarea (id может варьироваться).
        return mark_safe(
            f'<div class="markdown-editor-wrap" '
            f'data-upload-url="/admin/blog/upload-image/" '
            f'data-preview-url="/admin/blog/preview/">'
            f'{textarea_html}'
            f'</div>'
        )
