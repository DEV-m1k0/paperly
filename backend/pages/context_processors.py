from shop.models import SiteSetting


def site_settings(request):
    return {"site": SiteSetting.load()}
