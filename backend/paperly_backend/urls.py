from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from pages.views import admin_login_redirect
from shop.admin_views import upload_image as admin_md_upload, preview as admin_md_preview

urlpatterns = [
    path("admin/login/", admin_login_redirect, name="admin-login-redirect"),
    # Endpoints для markdown-редактора в админке. Должны идти ДО
    # `admin.site.urls`, иначе Jazzmin/Django их не достанет.
    path("admin/blog/upload-image/", admin_md_upload, name="admin-md-upload"),
    path("admin/blog/preview/", admin_md_preview, name="admin-md-preview"),
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
