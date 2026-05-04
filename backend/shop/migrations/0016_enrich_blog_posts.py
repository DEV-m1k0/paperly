"""
Data-migration: обогащает существующие посты блога markdown-разметкой.

Берёт контент из shop.blog_seed.RICH_BLOG_POSTS и применяет к постам
с совпадающим slug (post-1..post-12). Если поста с таким slug нет — создаёт.
Если существующий пост УЖЕ содержит markdown-разметку (есть `# `, `**` или
callout `> [!`) — пропускает, чтобы не перезаписать ручные правки.

Обратная миграция (reverse) ничего не делает: откатывать обогащение
автоматически бессмысленно — это потеря данных.
"""
from django.db import migrations
from django.utils import timezone


def _looks_like_markdown(text: str) -> bool:
    """Эвристика: если в content уже есть markdown-маркеры — не трогаем."""
    if not text:
        return False
    markers = ("\n# ", "\n## ", "\n**", "> [!", "```", "\n| ", "@[youtube]", "@[vk]")
    return any(m in text for m in markers)


def enrich_posts(apps, schema_editor):
    BlogPost = apps.get_model("shop", "BlogPost")
    BlogCategory = apps.get_model("shop", "BlogCategory")

    # Импорт RICH_BLOG_POSTS — НЕ через apps.get_model, это просто константа
    from shop.blog_seed import RICH_BLOG_POSTS

    # Гарантируем, что нужные категории существуют
    cat_titles = {"tips": "Советы", "reviews": "Обзоры", "news": "Новости"}
    cats = {}
    for slug, title in cat_titles.items():
        cat, _ = BlogCategory.objects.get_or_create(slug=slug, defaults={"title": title})
        cats[slug] = cat

    now = timezone.now()
    from datetime import timedelta

    enriched = 0
    skipped = 0
    created = 0

    for idx, post_data in enumerate(RICH_BLOG_POSTS):
        slug = post_data["slug"]
        existing = BlogPost.objects.filter(slug=slug).first()
        if existing is None:
            # Поста нет — создаём
            BlogPost.objects.create(
                slug=slug,
                title=post_data["title"],
                category=cats.get(post_data["category"]),
                excerpt=post_data["excerpt"],
                content=post_data["content"],
                status="published",
                published_at=now - timedelta(days=idx * 5),
            )
            created += 1
            continue

        # Пост есть. Проверяем — не редактировал ли его контент-менеджер
        # (markdown-маркеры присутствуют) — если да, не трогаем.
        if _looks_like_markdown(existing.content):
            skipped += 1
            continue

        existing.title = post_data["title"]
        existing.excerpt = post_data["excerpt"]
        existing.content = post_data["content"]
        if cats.get(post_data["category"]):
            existing.category = cats[post_data["category"]]
        existing.save(update_fields=["title", "excerpt", "content", "category", "updated_at"])
        enriched += 1

    print(f"  blog enrichment: enriched={enriched}, created={created}, skipped={skipped}")


def noop_reverse(apps, schema_editor):
    """Reverse — no-op. Откатывать обогащение бессмысленно."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0015_about_delivery_wholesale_pages"),
    ]

    operations = [
        migrations.RunPython(enrich_posts, noop_reverse),
    ]
