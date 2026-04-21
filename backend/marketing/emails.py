"""
Email sending helpers for newsletter subscriptions and campaigns.

Uses Django's templating + multipart email so we ship both a pretty HTML
version and a plain-text fallback (spam scorers like that; so do mail clients
that hide images by default).
"""

from __future__ import annotations

import logging
from typing import Iterable

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)

WELCOME_PROMO_CODE = "PAPERLY10"


def _site_url(request=None) -> str:
    """Best-effort absolute URL to the site root."""
    if request is not None:
        return f"{request.scheme}://{request.get_host()}"
    explicit = getattr(settings, "SITE_URL", "") or ""
    if explicit:
        return explicit.rstrip("/")
    hosts = getattr(settings, "ALLOWED_HOSTS", []) or []
    host = next((h for h in hosts if h and h not in ("*", "localhost", "127.0.0.1")), "")
    if host:
        return f"https://{host}"
    return "http://localhost:8000"


def _site_context(request=None) -> dict:
    """Shared context injected into every email template."""
    from shop.models import SiteSetting
    site = SiteSetting.load()
    return {
        "site_name": site.site_name or "Paperly",
        "site_city": site.city,
        "site_address": site.address,
        "site_phone": site.phone,
        "site_email": site.email,
        "site_url": _site_url(request),
    }


def _unsubscribe_url(subscriber, request=None) -> str:
    path = reverse("newsletter_unsubscribe", args=[subscriber.unsubscribe_token])
    return f"{_site_url(request)}{path}"


def _send_multipart(subject: str, html: str, text: str, to: list[str]) -> bool:
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "") or getattr(settings, "EMAIL_HOST_USER", "")
    try:
        msg = EmailMultiAlternatives(subject=subject, body=text, from_email=from_email, to=to)
        msg.attach_alternative(html, "text/html")
        msg.send(fail_silently=False)
        return True
    except Exception:
        logger.exception("Failed to send email to %s", to)
        return False


def send_welcome_email(subscriber, request=None) -> bool:
    """Sent immediately after a new subscription."""
    context = _site_context(request)
    context.update({
        "preview": "Спасибо, что подписались! Держите промокод на первый заказ.",
        "subject": f"Добро пожаловать в {context['site_name']}",
        "header_note": "канцтовары с заботой",
        "unsubscribe_url": _unsubscribe_url(subscriber, request),
        "welcome_promo": WELCOME_PROMO_CODE,
    })
    html = render_to_string("emails/welcome.html", context)
    text = render_to_string("emails/welcome.txt", context)
    return _send_multipart(context["subject"], html, text, [subscriber.email])


def _split_rows(items: list, per_row: int = 2) -> list[list]:
    return [items[i:i + per_row] for i in range(0, len(items), per_row)]


def send_campaign(campaign, subscribers: Iterable | None = None, request=None, is_test: bool = False) -> int:
    """Send a campaign to all active subscribers (or a custom list).

    Returns the number of emails successfully dispatched. Set ``is_test=True``
    to skip updating the campaign's status/sent_count (useful for preview sends
    to the staff user's own mailbox).
    """
    from shop.models import NewsletterSubscriber

    if subscribers is None:
        subscribers = NewsletterSubscriber.objects.filter(is_active=True)

    context_base = _site_context(request)
    cta_url = campaign.cta_url or "/catalog/"
    cta_absolute = cta_url if cta_url.startswith("http") else f"{context_base['site_url']}{cta_url}"

    products = list(campaign.featured_products.select_related("brand").prefetch_related("images")[:6])
    for product in products:
        image = product.images.first() if product.images.exists() else None
        product.image_url = ""
        if image:
            try:
                if image.image:
                    product.image_url = f"{context_base['site_url']}{image.image.url}"
                elif image.image_url:
                    product.image_url = image.image_url
            except Exception:
                product.image_url = getattr(image, "image_url", "") or ""

    sent = 0
    for subscriber in subscribers:
        context = dict(context_base)
        context.update({
            "preview": campaign.preview or strip_tags(campaign.intro_html)[:140],
            "subject": campaign.subject,
            "header_note": "свежая подборка",
            "campaign": campaign,
            "products": products,
            "product_rows": _split_rows(products, per_row=2),
            "cta_absolute_url": cta_absolute,
            "unsubscribe_url": _unsubscribe_url(subscriber, request),
        })
        html = render_to_string("emails/campaign.html", context)
        text = render_to_string("emails/campaign.txt", {**context, "campaign": campaign})
        if _send_multipart(campaign.subject, html, text, [subscriber.email]):
            sent += 1

    if not is_test:
        campaign.sent_count = sent
        campaign.sent_at = timezone.now()
        campaign.status = campaign.__class__.Status.SENT
        campaign.save(update_fields=["sent_count", "sent_at", "status", "updated_at"])
    return sent
