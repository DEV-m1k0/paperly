"""
Data migration: создать SitePage для privacy/offer/cookies с текстом
из `pages.legal_content`, чтобы админ сразу видел их в /admin/ и мог
править. При откате — удаляет только эти 3 записи.

Идемпотентно: если записи уже существуют, используется `get_or_create`.
"""

from django.db import migrations


LEGAL_SLUGS = {
    "privacy": "politika-konfidencialnosti",
    "offer":   "publichnaya-oferta",
    "cookies": "politika-cookie",
}

LEGAL_TITLES = {
    "privacy": "Политика конфиденциальности",
    "offer":   "Публичная оферта",
    "cookies": "Политика использования cookie",
}

LEGAL_PAGE_TYPE = {
    "privacy": "privacy",
    "offer":   "offer",
    "cookies": "cookies",
}


def seed_legal_pages(apps, schema_editor):
    SitePage = apps.get_model("shop", "SitePage")
    # Ленивый импорт — миграции не должны зависеть от работы pages app при migrate.
    from pages.legal_content import LEGAL_FALLBACK

    for kind, slug in LEGAL_SLUGS.items():
        page_type = LEGAL_PAGE_TYPE[kind]
        new_content = LEGAL_FALLBACK.get(kind, "").strip()
        title = LEGAL_TITLES[kind]

        # Сначала смотрим, есть ли уже страница с таким page_type
        # (seed_demo_data мог её создать). Если да — обновляем существующую.
        existing = SitePage.objects.filter(page_type=page_type).first()
        if existing:
            # Обновляем только если контент короче нашего (не перезатираем
            # осмысленно заполненный админом текст).
            if len(existing.content or "") < len(new_content) / 2:
                existing.title = title
                existing.content = new_content
                existing.is_published = True
                if not existing.slug or existing.slug in ("privacy", "offer", "cookies", "terms"):
                    existing.slug = slug
                existing.save()
        else:
            SitePage.objects.create(
                slug=slug,
                title=title,
                page_type=page_type,
                content=new_content,
                is_published=True,
            )


def unseed_legal_pages(apps, schema_editor):
    SitePage = apps.get_model("shop", "SitePage")
    SitePage.objects.filter(slug__in=LEGAL_SLUGS.values()).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("shop", "0011_add_cookies_pagetype"),
    ]

    operations = [
        migrations.RunPython(seed_legal_pages, reverse_code=unseed_legal_pages),
    ]
