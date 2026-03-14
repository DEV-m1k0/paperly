import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "dev-secret-key-change-me"
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "jazzmin",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "shop",  # Data/domain layer (models + admin)
    "pages",  # Template pages (landing + static/info pages)
    "catalog",  # Catalog domain API
    "customers",  # Customer profile/favorites API
    "checkout",  # Cart/order API
    "marketing",  # Promotions/blog/site pages/wholesale API
    "logistics",  # Pickup points and delivery tariffs API
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "paperly_backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "paperly_backend.wsgi.application"
ASGI_APPLICATION = "paperly_backend.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.yandex.ru'
EMAIL_PORT = 465
EMAIL_USE_SSL = True          # обязательно для порта 465
EMAIL_USE_TLS = False         # не используйте TLS одновременно с SSL
EMAIL_HOST_USER = 'paperly.work@yandex.ru'      # ваш полный адрес
EMAIL_HOST_PASSWORD = 'jrizrwwkbtcgbljp'   # ваш пароль (обычный или пароль приложения)
DEFAULT_FROM_EMAIL = 'paperly.work@yandex.ru'   # обычно совпадает с EMAIL_HOST_USER
SERVER_EMAIL = EMAIL_HOST_USER                  # для писем об ошибках сервера (опционально)

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = os.path.join(STATICFILES_DIRS[0], 'staticfiles') 
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# DRF baseline
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

# Celery baseline
CELERY_BROKER_URL = "redis://localhost:6379/0"
CELERY_RESULT_BACKEND = "redis://localhost:6379/1"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60

# Auth/email defaults
LOGIN_URL = "/auth/"

# Jazzmin admin customization
JAZZMIN_SETTINGS = {
    "site_title": "Paperly Admin",
    "site_header": "Paperly",
    "site_brand": "Paperly Admin",
    "site_logo_classes": "img-circle",
    "welcome_sign": "Панель управления магазином канцтоваров",
    "copyright": "Paperly",
    "search_model": [
        "auth.User",
        "shop.Product",
        "shop.Order",
        "shop.WholesaleRequest",
    ],
    "topmenu_links": [
        {"name": "Сайт", "url": "home", "permissions": ["auth.view_user"]},
        {"model": "shop.Order"},
        {"model": "shop.Product"},
        {"app": "shop"},
    ],
    "usermenu_links": [
        {"name": "Перейти на сайт", "url": "home"},
    ],
    "show_sidebar": True,
    "navigation_expanded": True,
    "hide_apps": [],
    "hide_models": [],
    "order_with_respect_to": [
        "shop",
        "shop.Order",
        "shop.Cart",
        "shop.Product",
        "shop.Category",
        "shop.Brand",
        "shop.Promotion",
        "shop.ProductReview",
        "shop.WholesaleRequest",
        "auth",
    ],
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "auth.group": "fas fa-user-friends",
        "shop.category": "fas fa-sitemap",
        "shop.brand": "fas fa-copyright",
        "shop.product": "fas fa-box-open",
        "shop.productimage": "fas fa-image",
        "shop.productspecification": "fas fa-list-check",
        "shop.productreview": "fas fa-star",
        "shop.promotion": "fas fa-tags",
        "shop.giftcertificate": "fas fa-gift",
        "shop.blogcategory": "fas fa-folder-open",
        "shop.blogpost": "fas fa-newspaper",
        "shop.pickuppoint": "fas fa-map-marker-alt",
        "shop.deliverytariff": "fas fa-truck",
        "shop.customerprofile": "fas fa-id-badge",
        "shop.address": "fas fa-map-marked-alt",
        "shop.notificationsetting": "fas fa-bell",
        "shop.favorite": "fas fa-heart",
        "shop.cart": "fas fa-shopping-cart",
        "shop.cartitem": "fas fa-cart-plus",
        "shop.order": "fas fa-file-invoice",
        "shop.orderitem": "fas fa-receipt",
        "shop.orderstatushistory": "fas fa-history",
        "shop.wholesalepricelist": "fas fa-file-alt",
        "shop.wholesalerequest": "fas fa-handshake",
        "shop.returnrequest": "fas fa-undo",
        "shop.returnrequestitem": "fas fa-reply",
        "shop.sitepage": "fas fa-file",
    },
    "related_modal_active": True,
    "custom_css": "css/admin-custom.css",
    "custom_js": "js/admin-custom.js",
    "changeform_format": "horizontal_tabs",
}

JAZZMIN_UI_TWEAKS = {
    "theme": "flatly",
    "default_theme_mode": "light",
    "navbar": "navbar-white navbar-light",
    "no_navbar_border": True,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-light-info",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "body_small_text": False,
    "brand_small_text": False,
    "accent": "accent-info",
    "button_classes": {
        "primary": "btn btn-info",
        "secondary": "btn btn-outline-secondary",
        "info": "btn btn-info",
        "warning": "btn btn-info",
        "danger": "btn btn-danger",
        "success": "btn btn-success",
    },
}



