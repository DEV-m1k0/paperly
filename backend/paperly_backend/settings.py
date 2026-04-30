import os
from pathlib import Path

from django.utils.translation import gettext_lazy as _
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DEBUG = os.environ.get("DEBUG", "False") == "True"
if DEBUG:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
else:
    SECRET_KEY = os.environ["SECRET_KEY"]
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]

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
    # WhiteNoise — раздача static + media на production без nginx.
    # Наш subclass добавляет MEDIA_ROOT к дефолтному STATIC_ROOT.
    "paperly_backend.middleware.MediaWhiteNoiseMiddleware",
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
                "pages.context_processors.site_settings",
                "shop.context_processors.admin_notifications",
            ],
        },
    },
]

WSGI_APPLICATION = "paperly_backend.wsgi.application"
ASGI_APPLICATION = "paperly_backend.asgi.application"

# ── Database ──
# Локально: SQLite (как было). На Render/Heroku/etc. — DATABASE_URL.
# Формат: postgres://user:pass@host:5432/dbname
if os.environ.get("DATABASE_URL"):
    try:
        import dj_database_url
        DATABASES = {
            "default": dj_database_url.parse(
                os.environ["DATABASE_URL"],
                conn_max_age=600,           # persistent connections
                ssl_require=not DEBUG,       # SSL для managed Postgres
            ),
        }
    except ImportError:
        # Fallback — если dj_database_url не установлен
        DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.yandex.ru')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '465'))
EMAIL_USE_SSL = os.environ.get('EMAIL_USE_SSL', 'True') == 'True'
EMAIL_USE_TLS = False
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER)
SERVER_EMAIL = EMAIL_HOST_USER

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
STATIC_ROOT = BASE_DIR / "staticfiles"

# WhiteNoise — сжатие и cache-busting для static'ов в production
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
WHITENOISE_MAX_AGE = 60 * 60 * 24 * 30   # 30 дней кеша в браузере
# Не падать, если минифицированный JS/CSS ссылается на .map-файл,
# которого нет в бандле (типично для bootstrap.bundle.min.js → *.map).
WHITENOISE_MANIFEST_STRICT = False

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# CSRF: домены, которым доверяем для POST-запросов (нужно для production)
CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.environ.get(
    "CSRF_TRUSTED_ORIGINS", ""
).split(",") if o.strip()]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# DRF baseline
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/minute",
        "user": "200/minute",
        # Custom scopes — referenced via `throttle_scope` on individual views.
        # checkout: каст. throttling for guest order creation (защита от спама).
        "checkout": "10/minute",
    },
}

# ── Caching ──
# По умолчанию Django использует LocMemCache (per-process), что не работает
# между worker'ами. Если задан явный REDIS_URL — используем Redis. Иначе
# LocMem (приемлемо для одного worker'а в DEBUG / single-process деплое).
#
# Намеренно НЕ переиспользуем CELERY_BROKER_URL — он имеет дефолтное значение,
# и если Redis не запущен локально, кэш-операции падали бы при первом GET.
_REDIS_URL = os.environ.get("REDIS_URL", "").strip()
if _REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": _REDIS_URL,
            "TIMEOUT": 300,  # 5 минут default
            "KEY_PREFIX": "paperly",
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "paperly-default",
            "TIMEOUT": 300,
        }
    }

# ── Logging ──
# Без явной конфигурации Django скрывает большинство ошибок в production.
# Шлём логи в stdout/stderr, чтобы платформа (Render/Heroku/journald)
# забирала их штатно. Уровни легко переопределяются через env.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{asctime} [{levelname}] {name}: {message}",
            "style": "{",
        },
        "simple": {
            "format": "[{levelname}] {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose" if not DEBUG else "simple",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": os.environ.get("LOG_LEVEL", "INFO"),
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "django.request": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "django.security": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        # Наши приложения
        "checkout": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "marketing": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "catalog": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "shop": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}

# Celery baseline
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60

# Auth/email defaults
LOGIN_URL = "/auth/"

# Jazzmin admin customization — брендирована под дизайн основного сайта Paperly
JAZZMIN_SETTINGS = {
    # ── Branding ──
    # Все user-facing строки проходят через gettext_lazy — когда появится
    # вторая локаль, переводы подхватятся из locale/<lang>/LC_MESSAGES/
    # без правки кода.
    "site_title": _("Paperly — Панель управления"),
    "site_header": _("Paperly"),
    "site_brand": _("Paperly"),
    "site_logo": "img/paperly-mark-white.svg",       # shown in sidebar brand block
    "site_logo_classes": "paperly-brand-logo",       # targeted by admin-custom.css
    "site_icon": "img/paperly-mark.svg",             # favicon
    "login_logo": "img/paperly-logo-login.svg",      # login screen
    "login_logo_dark": "img/paperly-logo-login.svg",
    "welcome_sign": _("С возвращением! Вы в панели управления Paperly."),
    "copyright": _("Paperly · интернет-магазин канцтоваров"),

    # ── Search ──
    # Глобальный navbar-поиск рендерит по одной форме на каждую модель,
    # поэтому держим только 2 самые частые — остальные доступны через
    # стандартный list-search внутри каждого changelist'а.
    "search_model": [
        "shop.Product",
        "shop.Order",
    ],

    # ── Top menu ──
    "topmenu_links": [
        {"name": _("Сайт"), "url": "home", "new_window": False, "icon": "fas fa-globe"},
        {"name": _("Каталог"), "url": "/catalog/", "new_window": False, "icon": "fas fa-grip"},
        {"model": "shop.Order"},
        {"model": "shop.Product"},
    ],

    "usermenu_links": [
        {"name": _("Перейти на сайт"), "url": "home", "icon": "fas fa-external-link-alt"},
        {"model": "auth.user"},
    ],

    # ── Sidebar ──
    "show_sidebar": True,
    "navigation_expanded": False,          # collapsed groups — cleaner look
    "hide_apps": [],
    "hide_models": [
        "shop.GiftCertificate",
        # Inline-блоки HomePage — редактируются только из формы главной.
        "shop.HomeHeroCard",
        "shop.HomeCategoryCard",
        "shop.HomeFeature",
        # Inline-блоки AboutPage / DeliveryPage / WholesalePage.
        "shop.AboutFeature",
        "shop.AboutStep",
        "shop.AboutMissionBullet",
        "shop.AboutB2BBullet",
        "shop.DeliveryFreeCardItem",
        "shop.DeliveryStep",
        "shop.DeliveryPayMethod",
        "shop.DeliveryFAQ",
        "shop.WholesaleFeature",
        "shop.WholesaleStep",
        "shop.WholesaleSideBullet",
    ],
    "order_with_respect_to": [
        # Group 1: Магазин
        "shop",
        "shop.Order",
        "shop.OrderItem",
        "shop.OrderStatusHistory",
        "shop.Cart",
        "shop.CartItem",
        # Group 2: Каталог
        "shop.Product",
        "shop.ProductImage",
        "shop.ProductSpecification",
        "shop.Category",
        "shop.Brand",
        "shop.ProductReview",
        # Group 3: Маркетинг
        "shop.Promotion",
        "shop.PromoCode",
        "shop.PromoCodeRedemption",
        "shop.NewsletterSubscriber",
        "shop.NewsletterCampaign",
        "shop.BlogPost",
        "shop.BlogCategory",
        # Group 4: Логистика
        "shop.PickupPoint",
        "shop.DeliveryTariff",
        # Group 5: Клиенты
        "shop.CustomerProfile",
        "shop.Address",
        "shop.Favorite",
        "shop.NotificationSetting",
        "shop.WholesalePriceList",
        "shop.WholesaleRequest",
        "shop.ReturnRequest",
        "shop.ReturnRequestItem",
        # Group 6: Контент
        "shop.HomePage",
        "shop.AboutPage",
        "shop.DeliveryPage",
        "shop.WholesalePage",
        "shop.SitePage",
        "shop.SocialLink",
        "shop.SiteSetting",
        # Auth at the bottom
        "auth",
    ],

    # ── Icons (FontAwesome 5 Free — bundled with Jazzmin) ──
    "icons": {
        "auth": "fas fa-shield-halved",
        "auth.user": "fas fa-user",
        "auth.group": "fas fa-user-group",

        # Каталог
        "shop.category": "fas fa-sitemap",
        "shop.brand": "fas fa-certificate",
        "shop.product": "fas fa-box-open",
        "shop.productimage": "fas fa-images",
        "shop.productspecification": "fas fa-list-check",
        "shop.productreview": "fas fa-star",

        # Корзина / Заказы
        "shop.cart": "fas fa-shopping-cart",
        "shop.cartitem": "fas fa-cart-plus",
        "shop.order": "fas fa-file-invoice-dollar",
        "shop.orderitem": "fas fa-receipt",
        "shop.orderstatushistory": "fas fa-clock-rotate-left",

        # Маркетинг
        "shop.promotion": "fas fa-tags",
        "shop.promocode": "fas fa-ticket",
        "shop.promocoderedemption": "fas fa-check-double",
        "shop.newslettersubscriber": "fas fa-envelope-open-text",
        "shop.newslettercampaign": "fas fa-paper-plane",
        "shop.blogcategory": "fas fa-folder-open",
        "shop.blogpost": "fas fa-newspaper",

        # Логистика
        "shop.pickuppoint": "fas fa-map-location-dot",
        "shop.deliverytariff": "fas fa-truck-fast",

        # Клиенты
        "shop.customerprofile": "fas fa-id-card",
        "shop.address": "fas fa-location-dot",
        "shop.notificationsetting": "fas fa-bell",
        "shop.favorite": "fas fa-heart",

        # Опт / возвраты
        "shop.wholesalepricelist": "fas fa-file-invoice",
        "shop.wholesalerequest": "fas fa-handshake",
        "shop.returnrequest": "fas fa-rotate-left",
        "shop.returnrequestitem": "fas fa-reply",

        # Контент сайта
        "shop.homepage": "fas fa-house-laptop",
        "shop.aboutpage": "fas fa-circle-info",
        "shop.deliverypage": "fas fa-truck-fast",
        "shop.wholesalepage": "fas fa-warehouse",
        "shop.homeherocard": "fas fa-id-card-clip",
        "shop.homecategorycard": "fas fa-grip",
        "shop.homefeature": "fas fa-star-of-life",
        "shop.sitepage": "fas fa-file-lines",
        "shop.sitesetting": "fas fa-sliders",
        "shop.sociallink": "fas fa-share-nodes",
    },

    "default_icon_parents": "fas fa-folder",
    "default_icon_children": "fas fa-circle-dot",

    # ── UI / interaction ──
    "related_modal_active": True,
    "custom_css": "css/admin-custom.css",
    "custom_js": "js/admin-custom.js",
    "use_google_fonts_cdn": False,          # we load our own fonts
    "changeform_format": "horizontal_tabs",
    "show_ui_builder": False,
}

JAZZMIN_UI_TWEAKS = {
    "theme": "flatly",
    "dark_mode_theme": None,
    "navbar": "navbar-white navbar-light",
    "no_navbar_border": True,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-light-primary",    # white sidebar with our teal accents
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "body_small_text": False,
    "brand_small_text": False,
    "accent": "accent-teal",
    "brand_colour": False,
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-outline-secondary",
        "info": "btn-info",
        "warning": "btn-warning",          # amber — как на сайте, без подмены
        "danger": "btn-danger",
        "success": "btn-success",
    },
    "actions_sticky_top": True,
}

# Production security settings
if not DEBUG:
    # Проксирование: Render/Heroku/etc. ставит X-Forwarded-Proto=https,
    # Django должен это понять чтобы SSL_REDIRECT не зациклил запросы.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    USE_X_FORWARDED_HOST = True

    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
