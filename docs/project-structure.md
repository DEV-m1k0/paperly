# Project Structure Documentation

Документ описывает архитектуру, ответственность модулей и соглашения по данным/файлам для проекта `Paperly`.

## 1. Обзор архитектуры

Проект построен как Django-монолит с разделением на прикладные модули внутри каталога `backend/`.

Основные домены:

- `paperly_backend` — глобальная конфигурация Django: `settings`, `urls`, `wsgi`, `asgi`.
- `pages` — server-rendered страницы сайта, auth-сценарии, legal pages, контекст для публичных шаблонов.
- `shop` — основная предметная модель проекта: товары, категории, бренды, отзывы, заказы, промокоды, контентные страницы, настройки сайта, B2B-сущности, admin-конфигурация.
- `catalog` — REST API для каталога, категорий, брендов, отзывов и схемы фильтров.
- `checkout` — REST API корзины, позиций корзины, оформления заказа, промокодов и тестового SBP-потока.
- `customers` — REST API профиля, адресов, избранного и пользовательских настроек уведомлений.
- `logistics` — REST API пунктов самовывоза и тарифов доставки.
- `marketing` — REST API акций, блога, подписок, оптовых прайс-листов, оптовых заявок и инфо-страниц.

Архитектурно проект сочетает две модели доставки:

- публичный UI рендерится через Django templates (`pages`);
- интерактивные блоки и клиентские сценарии получают данные через REST API (`catalog`, `checkout`, `customers`, `logistics`, `marketing`).

## 2. Корневая структура

```text
.
├─ backend/
│  ├─ .venv/
│  ├─ catalog/
│  ├─ checkout/
│  ├─ customers/
│  ├─ logistics/
│  ├─ marketing/
│  ├─ media/
│  ├─ pages/
│  ├─ paperly_backend/
│  ├─ shop/
│  ├─ static/
│  ├─ staticfiles/
│  ├─ templates/
│  ├─ .env.example
│  ├─ db.sqlite3
│  ├─ manage.py
│  └─ requirements.txt
├─ deploy/
├─ docs/
├─ build.sh
├─ README.md
└─ render.yaml
```

Примечание:

- фактический Django-проект живёт внутри `backend/`;
- `deploy/` и `render.yaml` относятся к деплою и окружению, а не к runtime-доменам приложения.

## 3. Django-модули

### 3.1 `backend/paperly_backend`

Назначение:

- глобальные настройки Django;
- корневой URLConf;
- точки входа WSGI/ASGI;
- подключение всех API и публичных маршрутов.

Ключевые файлы:

- `settings.py` — конфигурация приложения, Jazzmin, static/media, DRF, env vars;
- `urls.py` — объединяет `admin/`, `api/` и публичные `pages.urls`;
- `wsgi.py`, `asgi.py` — production entrypoints.

### 3.2 `backend/pages`

Назначение:

- главная страница и все server-rendered публичные страницы;
- авторизация, регистрация, logout, восстановление пароля;
- legal pages и redirect со старых `.html`-маршрутов;
- подготовка контекста для шаблонов.

Особенности:

- использует единый `page_view`, который маппит `page_name` на template;
- собирает SEO-метаданные и prefill-данные для checkout;
- содержит контекстные счётчики и витринные данные для home/about.

Ключевые файлы:

- `urls.py` — маршруты `/`, `/catalog/`, `/product/`, `/cart/`, `/auth/`, `/blog/` и др.;
- `views.py` — рендер страниц, auth flow, legal flow;
- `forms.py` — формы логина, регистрации и восстановления доступа;
- `context_processors.py` — глобальные данные сайта и соцсети.

### 3.3 `backend/shop`

Назначение:

- центральная доменная модель проекта;
- каталог и товарные сущности;
- заказы, корзина, промокоды, возвраты, B2B;
- контентные страницы и настройки сайта;
- конфигурация админки и data seeding.

Внутри `shop` находятся модели для:

- каталога: `Product`, `Category`, `Brand`, `CatalogFilterGroup`, `CatalogFilterOption`;
- клиентского слоя: `CustomerProfile`, `Address`, `Favorite`, `NotificationSetting`, `Cart`;
- заказов: `Order`, `OrderItem`, `OrderStatusHistory`, `PromoCode`, `PromoCodeRedemption`, `ReturnRequest`;
- маркетинга и контента: `Promotion`, `BlogPost`, `BlogCategory`, `NewsletterSubscriber`, `NewsletterCampaign`, `SitePage`;
- логистики и B2B: `PickupPoint`, `DeliveryTariff`, `WholesaleRequest`, `WholesalePriceList`;
- singleton/page content: `SiteSetting`, `HomePage`, `AboutPage`, `DeliveryPage`, `WholesalePage`, `SocialLink`.

Ключевые файлы:

- `models.py` — основная предметная модель проекта;
- `admin.py` — admin classes, inline-формы, singleton pages;
- `admin_views.py` — служебные admin endpoints, например markdown image upload/preview;
- `signals.py` — синхронизация связанных данных и служебные реакции;
- `management/commands/` — `seed_demo_data`, `sync_demo_media`, `make_manager`, `fetch_wb_images`, `wb_export_mapping`.

### 3.4 `backend/catalog`

Назначение:

- API для публичного каталога.

Отвечает за:

- выдачу товаров;
- выдачу категорий и брендов;
- отзывы;
- метаданные каталога и схему фильтров.

Ключевые файлы:

- `api_views.py` — viewsets и API views;
- `api_urls.py` — `/api/products/`, `/api/categories/`, `/api/brands/`, `/api/reviews/`, `/api/catalog-filters/`, `/api/catalog-meta/`;
- `serializers.py` — сериализация каталожных сущностей.

### 3.5 `backend/checkout`

Назначение:

- API корзины и оформления заказа.

Отвечает за:

- корзину и позиции корзины;
- создание и просмотр заказов;
- валидацию промокодов;
- тестовый SBP payment flow.

Ключевые файлы:

- `api_views.py`;
- `api_urls.py`;
- `serializers.py`.

Маршруты включают:

- `/api/carts/`
- `/api/cart-items/`
- `/api/orders/`
- `/api/promo-codes/validate/`
- `/api/sbp-payments/...`

### 3.6 `backend/customers`

Назначение:

- API пользовательского кабинета.

Отвечает за:

- профиль;
- адреса;
- избранное;
- настройки уведомлений.

Ключевые файлы:

- `api_views.py`;
- `api_urls.py`;
- `serializers.py`.

### 3.7 `backend/logistics`

Назначение:

- API логистических справочников.

Отвечает за:

- пункты самовывоза;
- тарифы доставки.

Ключевой файл: `api_urls.py`.

### 3.8 `backend/marketing`

Назначение:

- API маркетингового и контентного слоя.

Отвечает за:

- акции;
- блог;
- подписку на рассылку;
- оптовые прайс-листы;
- оптовые заявки;
- инфо-страницы сайта.

Ключевые файлы:

- `api_views.py`;
- `api_urls.py`;
- `serializers.py`;
- `emails.py` — письма и email-контент для части маркетинговых сценариев.

## 4. Маршрутизация и потоки

Корневой роутинг описан в [backend/paperly_backend/urls.py](/C:/Users/Anton/Desktop/moneyV2/backend/paperly_backend/urls.py).

Высокоуровнево:

- `/admin/` — Django admin + Jazzmin + project overrides;
- `/api/` — REST endpoints из `catalog`, `customers`, `checkout`, `marketing`, `logistics`;
- `/` и все публичные страницы — `pages.urls`.

Потоки данных:

### 4.1 Каталог → корзина → заказ

`shop` (модели товара, цены, остатки) → `catalog` (API каталога) → `checkout` (корзина/заказ) → `pages` + `templates` + `static/js` (клиентский UX).

### 4.2 Профиль и персональные данные

`shop` (CustomerProfile, Address, Favorite, NotificationSetting) → `customers` API → `pages` (`profile`, `favorites`, `order-history`) → клиентские JS-модули.

### 4.3 Контент и маркетинг

`shop` (Promotion, BlogPost, SitePage, NewsletterSubscriber, WholesaleRequest) → `marketing` API → публичные страницы `/blog/`, `/promotions/`, `/wholesale/`.

## 5. Шаблоны и фронтенд

### 5.1 `backend/templates/`

Фактические основные разделы:

- `templates/admin/` — overrides для Django/Jazzmin admin;
- `templates/components/` — переиспользуемые блоки (`header`, `footer`, blog card);
- `templates/emails/` — HTML/email шаблоны.

Также в корне `templates/` лежат page-level шаблоны:

- `index.html`
- `catalog.html`
- `product.html`
- `cart.html`
- `auth.html`
- `profile.html`
- `brands.html`
- `blog.html`
- и другие server-rendered страницы.

Подход:

- `pages.views.page_view` выбирает шаблон по `page_name`;
- клиентская логика доинициализируется через JS-модули из `static/js`.

### 5.2 `backend/static/`

Основные каталоги:

- `static/css/` — page-level и admin CSS;
- `static/js/` — page-level и shared JS;
- `static/img/` — иконки, favicon, UI assets;
- `static/vendor/` — сторонние библиотеки.

Особенности:

- публичные страницы в основном используют отдельные CSS/JS по page name;
- админка использует `admin-custom.css`, `admin-manager.css`, `admin-custom.js` и template overrides;
- есть клиентский чат-виджет (`chat.js`) и каталог/checkout-флоу на vanilla JS.

## 6. Медиа и файловые соглашения

### 6.1 `backend/media/`

Содержит локальные и demo-медиа:

- `media/products/` — изображения товаров;
- `media/categories/` — изображения категорий;
- `media/brands/` — логотипы брендов;
- `media/blog/` — изображения для блога.

### 6.2 Принципы организации

- файлы группируются по домену;
- demo-изображения входят в локальную структуру проекта;
- для production поддерживается синхронизация в внешний storage через `sync_demo_media`.

## 7. Seed, роли и служебные команды

Основные management commands:

- `seed_demo_data.py` — наполнение БД demo-данными;
- `sync_demo_media.py` — синхронизация demo media;
- `make_manager.py` — выдача/снятие роли менеджера;
- `fetch_wb_images.py`, `wb_export_mapping.py` — утилиты для работы с внешними товарными данными.

Ролевая модель:

- `admin`/`admin2` создаются как `is_superuser=True`;
- менеджеры получают `is_staff=True` и группу `Менеджер`;
- права менеджера задаются миграциями `0010_create_manager_group.py` и `0017_expand_manager_permissions.py`.

## 8. Конфигурация и окружения

Основные точки:

- `backend/manage.py`
- `backend/paperly_backend/settings.py`
- `backend/paperly_backend/wsgi.py`
- `backend/paperly_backend/asgi.py`
- `backend/.env.example`

По умолчанию:

- локальная БД — `backend/db.sqlite3`;
- `MEDIA_ROOT` обслуживается Django в `DEBUG`;
- production media может быть вынесено в S3-compatible storage;
- деплойная конфигурация живёт в `render.yaml` и `build.sh`.

## 9. Практика для разработчиков

Рекомендуемый порядок анализа новой задачи:

1. `backend/paperly_backend/urls.py`
2. нужный модуль `pages` / `catalog` / `checkout` / `customers` / `logistics` / `marketing`
3. если речь о данных, почти всегда затем нужно смотреть `backend/shop/models.py`
4. соответствующий HTML-шаблон в `backend/templates/`
5. соответствующие `backend/static/css/*.css` и `backend/static/js/*.js`

Для админки:

1. `backend/shop/admin.py`
2. `backend/templates/admin/`
3. `backend/static/css/admin-*.css`
4. `backend/static/js/admin-custom.js`

## 10. Контроль качества

Минимальная ручная проверка:

```bash
cd backend
python manage.py check
python manage.py migrate
```

Для smoke-проверки полезно пройти:

- `/`
- `/catalog/`
- `/product/?id=<id>`
- `/cart/`
- `/profile/`
- `/blog/`
- `/brands/`
- `/wholesale/`
- `/admin/`

Для задач, затрагивающих данные:

- повторный `seed_demo_data` при необходимости;
- выборочная проверка через admin и API endpoints.

