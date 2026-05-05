# Paperly — интернет-магазин канцтоваров

Paperly — полнофункциональный интернет-магазин канцелярии на Django 4.2 и Django REST Framework. В проекте есть публичный каталог, корзина, оформление заказов, личный кабинет, блог, B2B-раздел, кастомизированная Jazzmin-админка и большой demo seed для разработки.

Проект рассчитан на локальную разработку без внешних обязательных сервисов: SQLite, локальные media-файлы и vanilla JS. Redis/Celery, SMTP и PostgreSQL подключаются опционально для production-сценариев.

---

## Возможности

- **Каталог товаров** — 100 demo-товаров, категории, бренды, фильтры, поиск, сортировка, карточки с изображениями.
- **Товарные изображения** — seed генерирует уникальные предметные картинки для каждого товара; опционально можно использовать remote image URL через `--remote-images`.
- **Корзина и избранное** — работают для гостей через `localStorage` и для авторизованных пользователей через API.
- **Оформление заказа** — курьер/самовывоз, способы оплаты, промокоды, транзакционная защита остатков.
- **Личный кабинет** — профиль, адреса, уведомления, история заказов, избранное, возвраты.
- **Маркетинг** — акции, промокоды, блог, подписчики и email-кампании.
- **B2B** — оптовые заявки, прайс-листы, отдельная страница для юрлиц/школ/университетов.
- **Логистика** — пункты самовывоза и тарифы доставки.
- **Админка** — кастомизированная Jazzmin-админка с адаптивной навигацией, фильтрами, действиями, inline-формами и dashboard-виджетами.
- **Чат-помощник** — клиентский виджет с готовыми сценариями и подборками товаров.

---

## Стек

| Слой | Технологии |
|---|---|
| Backend | Python 3.11+, Django 4.2, DRF 3.15 |
| Admin | django-jazzmin 3.0 + кастомные templates/static |
| DB | SQLite локально, PostgreSQL через `DATABASE_URL` |
| Frontend | Django templates, HTML, CSS, Vanilla JS, Bootstrap Icons, Choices.js |
| Media | Django `ImageField`, Pillow, локальные demo-файлы, S3-compatible storage через `django-storages` |
| Async | Celery + Redis опционально |
| Email | SMTP |

---

## Быстрый старт

```bash
git clone <url-репозитория>
cd moneyV2/backend
python -m venv .venv
.venv\Scripts\Activate.ps1      # Windows PowerShell
# source .venv/bin/activate      # Linux/macOS
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo_data
python manage.py runserver
```

Открыть сайт: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

Админка: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

---

## Переменные окружения

Создай `backend/.env` на основе `backend/.env.example` или вручную:

```env
SECRET_KEY=dev-secret-key-change-me
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Production DB, если нужно
# DATABASE_URL=postgres://user:password@host:5432/dbname

# Email
EMAIL_HOST=smtp.yandex.ru
EMAIL_PORT=465
EMAIL_USE_SSL=True
EMAIL_HOST_USER=your-email@yandex.ru
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=your-email@yandex.ru

# Media storage for Render/production
USE_S3_MEDIA=False
AWS_STORAGE_BUCKET_NAME=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_S3_REGION_NAME=auto
AWS_S3_ENDPOINT_URL=
AWS_S3_CUSTOM_DOMAIN=

# Redis/Celery, опционально
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
REDIS_URL=redis://localhost:6379/2
```

---

## Demo seed

Основная команда:

```bash
python manage.py seed_demo_data
python manage.py sync_demo_media
```

Полная очистка demo-данных и повторная заливка:

```bash
python manage.py seed_demo_data --reset
```

Опционально можно переключить товары на remote Unsplash URL вместо локально сгенерированных media-картинок:

```bash
python manage.py seed_demo_data --remote-images
```

Если в production включён S3-compatible storage, синхронизируйте bundled media-файлы в bucket:

```bash
python manage.py sync_demo_media
```

Что создаёт `seed_demo_data`:

- 100 товаров с уникальными SKU и изображениями.
- 10 брендов с сайтами и logo URL.
- Дерево категорий и фильтры каталога.
- 20 покупателей с профилями, адресами, корзинами, избранным, заказами и отзывами.
- 3 менеджера и 2 администратора.
- Заказы и история статусов за период более 6 месяцев.
- Акции, промокоды, подарочные сертификаты.
- Пункты самовывоза, тарифы доставки.
- Блог, инфо-страницы и настройки сайта.
- Оптовые прайс-листы, заявки на опт и заявки на возврат.
- Записи в `django_admin_log`, чтобы админка выглядела как живой проект.

---

## Демо-доступы

Вход покупателей: `/auth/`  
Вход менеджеров и админов: `/admin/`

### Покупатели

Пароль для всех покупателей: `customer12345`

| Пользователь | Email | Пароль | Имя |
|---|---|---|---|
| `customer` | `customer@paperly.ru` | `customer12345` | Артем Власов |
| `customer2` | `customer2@paperly.ru` | `customer12345` | Мария Сидорова |
| `customer3` | `customer3@paperly.ru` | `customer12345` | Дмитрий Соколов |
| `customer4` | `customer4@paperly.ru` | `customer12345` | Елена Иванова |
| `customer5` | `customer5@paperly.ru` | `customer12345` | Павел Козлов |
| `customer6` | `customer6@paperly.ru` | `customer12345` | Ольга Смирнова |
| `customer7` | `customer7@paperly.ru` | `customer12345` | Алексей Попов |
| `customer8` | `customer8@paperly.ru` | `customer12345` | Наталья Фёдорова |
| `customer9` | `customer9@paperly.ru` | `customer12345` | Михаил Волков |
| `customer10` | `customer10@paperly.ru` | `customer12345` | Татьяна Морозова |
| `customer11` | `customer11@paperly.ru` | `customer12345` | Кирилл Беляев |
| `customer12` | `customer12@paperly.ru` | `customer12345` | Софья Орлова |
| `customer13` | `customer13@paperly.ru` | `customer12345` | Виктор Громов |
| `customer14` | `customer14@paperly.ru` | `customer12345` | Алина Егорова |
| `customer15` | `customer15@paperly.ru` | `customer12345` | Роман Титов |
| `customer16` | `customer16@paperly.ru` | `customer12345` | Вера Лебедева |
| `customer17` | `customer17@paperly.ru` | `customer12345` | Георгий Семенов |
| `customer18` | `customer18@paperly.ru` | `customer12345` | Полина Зайцева |
| `customer19` | `customer19@paperly.ru` | `customer12345` | Илья Фомин |
| `customer20` | `customer20@paperly.ru` | `customer12345` | Дарья Крылова |

### Менеджеры

Пароль для всех менеджеров: `manager12345`

| Пользователь | Email | Пароль | Имя |
|---|---|---|---|
| `manager` | `manager@paperly.ru` | `manager12345` | Екатерина Романова |
| `manager2` | `manager2@paperly.ru` | `manager12345` | Игорь Белов |
| `manager3` | `manager3@paperly.ru` | `manager12345` | Ксения Новикова |

Менеджеры имеют `is_staff=True` и входят в группу `Менеджер`. Группа создаётся миграцией и даёт права на рабочие разделы админки без суперпользовательского доступа.

### Администраторы

Пароль для всех администраторов: `admin12345`

| Пользователь | Email | Пароль | Имя |
|---|---|---|---|
| `admin` | `admin@paperly.ru` | `admin12345` | Admin Paperly |
| `admin2` | `admin2@paperly.ru` | `admin12345` | Сергей Николаев |

> Demo-пароли нужны только для разработки. Перед production удалите demo-пользователей или смените пароли.

---

## Роли

| Роль | Доступ | Назначение |
|---|---|---|
| Покупатель | `/auth/`, пользовательские страницы | покупки, избранное, корзина, история заказов |
| Менеджер | `/admin/` | операционная работа в админке по выданным permissions |
| Администратор | `/admin/` | полный доступ к админке и настройкам |

Назначить/снять роль менеджера можно командой:

```bash
python manage.py make_manager <username-or-email>
python manage.py make_manager <username-or-email> --revoke
```

---

## Основные страницы

| URL | Назначение |
|---|---|
| `/` | Главная страница |
| `/catalog/` | Каталог товаров с фильтрами и сортировкой |
| `/product/?id=<id>` | Страница товара |
| `/cart/` | Корзина и checkout |
| `/favorites/` | Избранное |
| `/profile/` | Профиль покупателя |
| `/order-history/` | История заказов |
| `/auth/` | Вход, регистрация, восстановление пароля |
| `/about/` | О магазине |
| `/delivery/` | Доставка и оплата |
| `/guarantee/` | Гарантия и возврат |
| `/pickup/` | Пункты самовывоза |
| `/brands/` | Бренды |
| `/promotions/` | Акции |
| `/bestsellers/` | Хиты продаж |
| `/new-arrivals/` | Новинки |
| `/blog/` | Блог |
| `/wholesale/` | Оптовым клиентам |
| `/admin/` | Админка |

---

## REST API

| Метод | URL | Доступ | Описание |
|---|---|---|---|
| GET | `/api/products/` | public | Товары, поиск, фильтры, сортировка, пагинация |
| GET | `/api/products/{id}/` | public | Деталка товара |
| GET | `/api/categories/` | public | Категории |
| GET | `/api/brands/` | public | Бренды |
| GET | `/api/catalog-filters/` | public | Схема фильтров каталога |
| GET | `/api/catalog-meta/` | public | Метаданные каталога |
| GET | `/api/reviews/` | public | Отзывы |
| GET/POST | `/api/favorites/` | user | Избранное |
| GET/POST | `/api/profiles/` | user | Профиль |
| GET/POST | `/api/addresses/` | user | Адреса |
| GET/POST | `/api/orders/` | mixed | История/создание заказов |
| GET | `/api/pickup-points/` | public | Пункты самовывоза |
| GET | `/api/delivery-tariffs/` | public | Тарифы доставки |
| GET | `/api/promotions/` | public | Акции |
| GET | `/api/blog-posts/` | public | Блог |
| POST | `/api/wholesale-requests/` | any | Оптовая заявка |

DRF throttling: `60/minute` для анонимов, `200/minute` для пользователей.

---

## Структура проекта

```text
backend/
├── paperly_backend/          # settings, urls, middleware, celery
├── shop/                     # основные модели, admin, signals, seed commands
├── catalog/                  # API каталога и фильтров
├── checkout/                 # API корзины, заказов, промокодов
├── customers/                # API профиля, адресов, избранного
├── logistics/                # API пунктов самовывоза и тарифов
├── marketing/                # API блога, акций, рассылок, B2B
├── pages/                    # server-rendered страницы и auth views
├── templates/                # HTML-шаблоны сайта и admin overrides
├── static/                   # CSS, JS, vendor assets
├── media/                    # generated/uploaded media
├── manage.py
└── requirements.txt
```

---

## Полезные команды

```bash
# Django
python manage.py runserver
python manage.py check
python manage.py migrate
python manage.py makemigrations
python manage.py seed_demo_data
python manage.py seed_demo_data --reset
python manage.py seed_demo_data --remote-images
python manage.py sync_demo_media
python manage.py createsuperuser
python manage.py make_manager <username-or-email>
python manage.py make_manager <username-or-email> --revoke
python manage.py collectstatic
python manage.py shell

# Celery, если подключён Redis
celery -A paperly_backend worker -l info
celery -A paperly_backend beat -l info
```

---

## Админка

Админка находится на `/admin/`. В ней редактируются товары, категории, бренды, заказы, возвраты, акции, промокоды, блог, настройки сайта, страницы и B2B-данные.

В проекте переопределены admin-шаблоны и стили:

- адаптивный sidebar и navbar;
- drawer-фильтры changelist;
- адаптивные таблицы и inline-формы;
- sticky-блок действий на change form;
- dropdown быстрых действий/уведомлений;
- ссылка выхода на сайт из sidebar.

---

## Чат-помощник

Чат находится в `backend/static/js/chat.js` и работает на клиенте. Он не использует нейросети и не требует отдельного backend endpoint. Для товарных подборок обращается к `/api/products/`.

Публичный JS API:

```js
window.paperly.chat.open();
window.paperly.chat.goto("delivery");
window.paperly.chat.reset();
```

---

## Production notes

- Установите `DEBUG=False`.
- Задайте сильный `SECRET_KEY`.
- Настройте `ALLOWED_HOSTS` и `CSRF_TRUSTED_ORIGINS`.
- Подключите PostgreSQL через `DATABASE_URL`, если SQLite недостаточно.
- Для Render настройте media через S3-compatible bucket: `USE_S3_MEDIA=True`, `AWS_STORAGE_BUCKET_NAME`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_S3_ENDPOINT_URL`, `AWS_S3_REGION_NAME`; для публичного домена bucket задайте `AWS_S3_CUSTOM_DOMAIN`.
- Выполните `python manage.py collectstatic`.
- Выполните `python manage.py sync_demo_media`, чтобы загрузить `backend/media` в configured storage.
- Смените или удалите demo-пользователей.
- Настройте SMTP и Redis/Celery при необходимости.

---

## Типовые проблемы

### В каталоге не все товары
Проверьте `/api/products/?page_size=100`: API должен вернуть `count: 100` и 100 элементов в `results`. Каталог передаёт `page_size=100` из `backend/static/js/catalog.js`.

### В каталоге старые картинки
Браузер может держать кэш media-файлов. Serializer добавляет версию к URL изображения, но после ручной замены файлов можно жёстко обновить страницу или снова выполнить `seed_demo_data`.

### На Render нет картинок
Render free использует ephemeral filesystem: загруженные во время работы файлы пропадают после redeploy/restart. В проекте demo-картинки закоммичены в `backend/media`, а для надежного production-сценария подключается внешний bucket через `USE_S3_MEDIA=True`. После настройки env vars запустите deploy: `build.sh` выполнит `seed_demo_data` и `sync_demo_media`, загрузив bundled media в bucket.

### Не работает вход в админку
Убедитесь, что выполнены миграции и seed:

```bash
python manage.py migrate
python manage.py seed_demo_data
```

Затем используйте `admin@paperly.ru` / `admin12345`.

---

## Лицензия

Проект разработан для учебных и коммерческих целей.
