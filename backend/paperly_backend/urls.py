from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from pages.views import admin_login_redirect

urlpatterns = [
    path("admin/login/", admin_login_redirect, name="admin-login-redirect"),
    path("admin/", admin.site.urls),
    path("api/", include("catalog.api_urls")),
    path("api/", include("customers.api_urls")),
    path("api/", include("checkout.api_urls")),
    path("api/", include("marketing.api_urls")),
    path("api/", include("logistics.api_urls")),
    path("", include("pages.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
