from shop.models import SiteSetting, SocialLink


def site_settings(request):
    return {
        "site": SiteSetting.load(),
        "social_links": list(SocialLink.objects.filter(is_active=True).order_by("sort_order", "label")),
    }
