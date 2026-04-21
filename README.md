# Paperly — интернет-магазин канцтоваров

Полнофункциональный интернет-магазин канцелярии на Django 4.2 + DRF с локальным AI-ассистентом на Ollama. Полностью оффлайн: ни корзина, ни чат не делают запросов во внешние сервисы.

---

## Ключевые возможности

- **Каталог + фильтры** — 47 товаров, 33 категории, 10 брендов, многокритериальный поиск, сортировка, пагинация.
- **Гостевой шопинг** — корзина и избранное работают без регистрации (localStorage), аккаунт можно создать на этапе оформления заказа.
- **Заказы в 1 шаг** — курьер / самовывоз, 4 способа оплаты, транзакционная защита при создании.
- **Личный кабинет** — профиль, адреса, уведомления, история заказов, возвраты.
- **AI-ассистент** — плавающий чат-виджет с поддержкой товарного поиска (tool-calling). Работает **полностью локально** через Ollama, никаких внешних API.
- **Яндекс.Карта** — 7 пунктов самовывоза в Курске.
- **Блог** — категории, полные статьи.
- **B2B** — оптовые заявки, прайс-листы.
- **Админка Jazzmin** — всё редактируется через неё, включая статичные страницы.

---

## Стек

| Слой | Технологии |
|---|---|
| Backend | Python 3.11+, Django 4.2, DRF 3.15 |
| AI | Ollama (локальный LLM, OpenAI-compatible API) + `openai` Python SDK |
| Админка | django-jazzmin 3.0 |
| База | SQLite (dev), PostgreSQL (prod) |
| Фронт | HTML5, CSS3, Vanilla JS (ES6), Bootstrap Icons |
| Карты | Яндекс.Карты API 2.1 |
| Очереди | Celery 5.4 + Redis (опционально) |
| Email | SMTP |

---

## Быстрый старт

**TL;DR для тех, у кого Python и Ollama уже стоят:**

```bash
git clone <url>
cd moneyV2/backend
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate        # Linux/macOS
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo_data
python manage.py createsuperuser
python manage.py runserver
```

Открыть [http://127.0.0.1:8000/](http://127.0.0.1:8000/). При первом `runserver` кастомная команда сама запустит Ollama и скачает модель `llama3.2:3b` (~2 ГБ).

---

## Установка (подробно)

### 0. Что потребуется

| Инструмент | Зачем | Где взять |
|---|---|---|
| **Python 3.11+** | Django, SDK | [python.org/downloads](https://www.python.org/downloads/) |
| **Git** | склонировать проект | [git-scm.com](https://git-scm.com/) |
| **Ollama** | локальный AI-ассистент | [ollama.com/download](https://ollama.com/download) |
| **Redis** (опционально) | Celery, фоновые задачи | [redis.io/download](https://redis.io/download/) |

Если AI-чат тебе не нужен — Ollama можно не ставить, всё остальное будет работать (виджет просто вернёт «Ассистент недоступен»).

### 1. Клонирование

```bash
git clone <url-репозитория>
cd moneyV2
```

### 2. Виртуальное окружение

```bash
cd backend
python -m venv .venv
```

Активация:

```bash
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Windows (CMD / Git Bash)
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate
```

### 3. Python-зависимости

```bash
pip install -r requirements.txt
```

Ставятся: Django, DRF, Jazzmin, Celery, Pillow, `openai` (для AI-чата), `python-dotenv`.

### 4. Переменные окружения

Скопируй пример и поправь:

```bash
# в папке backend/
cp .env.example .env    # если есть
# или создай .env вручную (см. шаблон ниже)
```

**Шаблон `backend/.env`:**

```env
SECRET_KEY=dev-secret-key-change-me
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Email (для сброса пароля)
EMAIL_HOST=smtp.yandex.ru
EMAIL_PORT=465
EMAIL_USE_SSL=True
EMAIL_HOST_USER=your-email@yandex.ru
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=your-email@yandex.ru

# Celery (опционально)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# AI — локальная Ollama (дефолт; можно удалить — подставится автоматически)
AI_API_KEY=ollama
AI_API_BASE=http://localhost:11434/v1
AI_MODEL=llama3.2:3b
```

### 5. База данных

```bash
python manage.py migrate
python manage.py seed_demo_data
```

`seed_demo_data` создаст:
- 47 товаров с изображениями в 33 категориях
- 10 брендов с логотипами
- 11 групп фильтров
- 3 акции со скидками
- 7 пунктов самовывоза в Курске
- 4 тарифа доставки
- 6 статей блога в 3 категориях
- 9 инфо-страниц (О магазине, Доставка, Гарантия...)
- 4 подарочных сертификата
- 3 оптовых прайс-листа и 3 заявки
- 2 демо-покупателя с заказами в разных статусах
- 2 заявки на возврат
- Настройки сайта

Для полной перезагрузки:

```bash
python manage.py seed_demo_data --reset
```

### 6. Суперпользователь

```bash
python manage.py createsuperuser
```

### 7. Установка Ollama (для AI-чата)

1. Скачай и установи с [ollama.com/download](https://ollama.com/download) (~500 МБ)
2. **Закрой и открой новый терминал** — чтобы `ollama` появилась в PATH
3. Проверь: `ollama --version` должен вернуть номер версии

При первом `runserver` Django сам подтянет модель `llama3.2:3b` (~2 ГБ на диске). Заранее можно:

```bash
ollama pull llama3.2:3b
```

### 8. Запуск

```bash
python manage.py runserver
```

Первый запуск с Ollama выглядит так:

```
[ollama] starting `ollama serve`...
[ollama] daemon: started
[ollama] pulling `llama3.2:3b` — this may take several minutes...
[ollama] model `llama3.2:3b`: pulled
Starting development server at http://127.0.0.1:8000/
```

Последующие запуски — мгновенные: daemon остаётся в фоне.

---

## Демо-доступы

| Роль | URL | Логин | Пароль |
|---|---|---|---|
| Админка | `/admin/` | (твой суперпользователь) | (твой пароль) |
| Демо-покупатель 1 | `/auth/` | `demo` | `demo12345` |
| Демо-покупатель 2 | `/auth/` | `maria` | `maria12345` |

## Роли и права

В проекте две служебные роли (плюс обычный покупатель):

| Роль | Что может | Где живёт |
|---|---|---|
| **Суперпользователь** | всё — заказы, товары, настройки, пользователи | `createsuperuser` |
| **Менеджер** | модерировать отзывы, публиковать статьи блога + категории блога | группа «Менеджер», создаётся миграцией |
| **Покупатель** | обычный магазин: корзина, заказы, избранное | регистрация на сайте |

Группа **«Менеджер»** и её права настраиваются автоматически миграцией `shop/0010_create_manager_group.py` — она включает:
- Полный CRUD на **«Отзывы на товары»** (включая `is_published` — approve/reject)
- Полный CRUD на **«Блог-посты»** (draft/published)
- Полный CRUD на **«Категории блога»**
- Read-only доступ к товарам, брендам и категориям (для контекста)

При входе в `/admin/` менеджер видит **только** эти разделы — Django фильтрует сайдбар по permissions.

Назначить роль через CLI:

```bash
python manage.py make_manager demo              # выдать
python manage.py make_manager demo --revoke     # снять
python manage.py make_manager editor@paperly.ru # можно по email
```

Или через админку: **Auth → Users → выбрать пользователя → Groups → «Менеджер» → ✓ Staff status**.

---

## Структура проекта

```
backend/
├── paperly_backend/              # Главный конфиг Django
│   ├── settings.py               # БД, email, DRF, Jazzmin, AI
│   └── urls.py                   # Корневой роутер
├── shop/                         # Модели + админка (29 моделей)
│   ├── models.py                 # Product, Order, Category, Brand, ...
│   ├── admin.py                  # Jazzmin-конфиги
│   ├── apps.py                   # + patch SQLite LOWER для кириллицы
│   ├── signals.py                # История статусов заказов
│   ├── fixtures/seed_data.json
│   └── management/commands/
│       └── seed_demo_data.py     # Заливка демо-контента
├── pages/                        # SSR-страницы + AI-чат
│   ├── views.py                  # Auth, все лендинги
│   ├── chat_views.py             # POST /api/chat/ (агентик-луп)
│   ├── chat_prompts.py           # System prompt + tool schema + search
│   ├── urls.py
│   └── management/commands/
│       ├── ensure_ollama.py      # Стартует daemon + pull модели
│       └── runserver.py          # Drop-in замена runserver
├── catalog/                      # API каталога
├── customers/                    # API профилей/адресов/избранного
├── checkout/                     # API корзины/заказов
├── marketing/                    # API акций/блога/опта/страниц
├── logistics/                    # API пунктов/тарифов
├── templates/                    # HTML-шаблоны (~25 страниц)
│   └── components/header.html
├── static/
│   ├── css/                      # 22 CSS-файла (включая chat.css)
│   │   ├── theme.css             # Дизайн-система (токены, btn, card, ...)
│   │   └── chat.css              # Плавающий AI-виджет
│   └── js/                       # 17 JS-файлов
│       ├── utils.js              # window.paperly helpers
│       ├── header-search.js      # Live-поиск в хедере
│       └── chat.js               # AI-виджет
├── media/                        # Загруженные картинки
├── manage.py
└── requirements.txt
```

---

## AI-ассистент: как это работает

### Архитектура

```
Браузер (chat.js)
   ↓ POST /api/chat/ (session cookie + CSRF)
ChatAPIView  ─── rate-limit (60/час на сессию)
   ↓
build_system_prompt()  — вливаем живые данные (товары, бренды, тарифы)
   ↓
OpenAI SDK → http://localhost:11434/v1 (Ollama)
   ↓
Модель решает: отвечать текстом или вызвать tool
   ↓
Если tool_call search_products → run_product_search() в БД
   ↓
Результат обратно в модель, до 4 итераций
   ↓
Финальный ответ + [product:ID] маркеры → фронт рисует карточки
```

### Ключевые файлы

- **[backend/pages/chat_views.py](backend/pages/chat_views.py)** — HTTP-эндпоинт, агентик-луп, coerce типов, fallback-парсинг `tool_use_failed`.
- **[backend/pages/chat_prompts.py](backend/pages/chat_prompts.py)** — system prompt на русском (правила, инфо о магазине, стоп-слова), tool schema, `run_product_search()` (Lower + токенизация + стемминг для кириллицы).
- **[backend/shop/apps.py](backend/shop/apps.py)** — патч `LOWER`/`UPPER` функций SQLite для корректной работы с кириллицей.
- **[backend/pages/management/commands/ensure_ollama.py](backend/pages/management/commands/ensure_ollama.py)** — проверяет daemon, стартует при необходимости, пуллит модель.
- **[backend/pages/management/commands/runserver.py](backend/pages/management/commands/runserver.py)** — drop-in runserver, вызывает `ensure_ollama` перед стартом.
- **[backend/static/js/chat.js](backend/static/js/chat.js)** — виджет: кнопка-бабл, панель, localStorage-история, typing indicator, быстрые подсказки, рендер карточек товаров.
- **[backend/static/css/chat.css](backend/static/css/chat.css)** — стили в теме сайта (teal-градиент).

### Настройка модели

По умолчанию — `llama3.2:3b` (2 ГБ, быстрая, надёжный tool-calling). Сменить в `.env`:

| Модель | Размер | Когда |
|---|---|---|
| `llama3.2:1b` | 1.3 ГБ | слабое железо, tool-calling нестабилен |
| **`llama3.2:3b`** | **2 ГБ** | **дефолт — лучший баланс** |
| `qwen2.5:3b` | 1.9 ГБ | альтернатива, хорош для русского |
| `llama3.1:8b` | 4.7 ГБ | более умные ответы, нужно 8+ ГБ RAM |
| `qwen2.5:7b` | 4.4 ГБ | топ tool-calling среди малых моделей |
| `llama3.1:70b` | 40 ГБ | нужна GPU с 24+ ГБ VRAM |

### Использовать другого провайдера (вместо Ollama)

Код универсален — подставь любой OpenAI-compatible endpoint в `.env`:

```env
# Groq Cloud (бесплатный tier, быстро)
AI_API_KEY=gsk_...
AI_API_BASE=https://api.groq.com/openai/v1
AI_MODEL=llama-3.3-70b-versatile

# OpenRouter (куча моделей, часть бесплатных)
AI_API_KEY=sk-or-...
AI_API_BASE=https://openrouter.ai/api/v1
AI_MODEL=meta-llama/llama-3.1-8b-instruct:free

# OpenAI (платный)
AI_API_KEY=sk-...
AI_API_BASE=https://api.openai.com/v1
AI_MODEL=gpt-4o-mini
```

Custom runserver увидит, что `AI_API_BASE` не указывает на Ollama, и пропустит проверку daemon.

---

## REST API

| Метод | URL | Права | Описание |
|---|---|---|---|
| GET | `/api/products/` | public | Каталог + фильтры + поиск + пагинация |
| GET | `/api/products/{id}/` | public | Деталка товара |
| GET | `/api/categories/` | public | Дерево категорий |
| GET | `/api/brands/` | public | Бренды + счётчики |
| GET | `/api/filter-groups/` | public | Группы фильтров |
| GET | `/api/promotions/` | public | Активные акции |
| GET | `/api/blog-posts/` | public | Статьи блога |
| GET | `/api/pickup-points/` | public | Пункты самовывоза |
| GET | `/api/delivery-tariffs/` | public | Тарифы доставки |
| POST | `/api/chat/` | session | AI-ассистент (tool-use агентик-луп) |
| POST | `/api/orders/` | any | Создание заказа (гостевой OK) |
| GET | `/api/orders/` | user | История заказов |
| GET/POST | `/api/favorites/` | user | Избранное |
| GET/POST | `/api/profiles/` | user | Профиль |
| GET/POST | `/api/addresses/` | user | Адреса |
| POST | `/api/wholesale-requests/` | any | Оптовая заявка |

Rate-limits (DRF throttling): **60 req/min** для анонимов, **200 req/min** для авторизованных. Чат: **60 сообщений/час** на сессию.

---

## Страницы

| URL | Описание |
|---|---|
| `/` | Главная (каталог, новинки, хиты, акции) |
| `/catalog/` | Каталог с фильтрами и сортировкой |
| `/product/?id=N` | Карточка товара |
| `/cart/` | Корзина + 1-шаг чекаут |
| `/favorites/` | Избранное (гостям тоже доступно) |
| `/profile/` | Личный кабинет |
| `/order-history/` | История заказов |
| `/auth/` | Вход / регистрация / сброс пароля |
| `/about/` | О магазине |
| `/delivery/` | Доставка и оплата |
| `/guarantee/` | Гарантия и возврат |
| `/pickup/` | Пункты самовывоза (Яндекс.Карта) |
| `/brands/` | Бренды |
| `/promotions/` | Акции |
| `/bestsellers/` | Хиты продаж |
| `/new-arrivals/` | Новинки |
| `/blog/` | Блог |
| `/wholesale/` | Для юрлиц |
| `/legal/privacy/` | Политика конфиденциальности |
| `/legal/terms/` | Публичная оферта |
| `/legal/cookies/` | О cookies |

---

## Полезные команды

```bash
# Django
python manage.py runserver                  # старт + auto-Ollama
python manage.py migrate                    # применить миграции
python manage.py makemigrations             # создать миграции
python manage.py seed_demo_data             # загрузить демо
python manage.py seed_demo_data --reset     # полная перезагрузка
python manage.py createsuperuser            # админ
python manage.py make_manager <user>        # выдать роль «Менеджер»
python manage.py make_manager <user> --revoke  # снять роль
python manage.py collectstatic              # собрать статику (prod)
python manage.py shell                      # shell с Django-окружением

# AI / Ollama
python manage.py ensure_ollama              # проверить + запустить + pull
python manage.py ensure_ollama --check      # только проверить (exit 1 если нет)
ollama list                                 # какие модели скачаны
ollama pull qwen2.5:3b                      # скачать другую модель
ollama rm llama3.2:3b                       # удалить модель

# Celery (если нужно)
celery -A paperly_backend worker -l info
celery -A paperly_backend beat -l info
```

---

## Редактирование контента через админку

Инфо-страницы (О магазине, Доставка, Гарантия и др.) лежат в **Админка → Инфо-страницы**. Поле **«Содержание (HTML)»**:

- Пусто → страница показывает дефолтный дизайн из шаблона.
- Заполнено → рендерится твой HTML.

Также через админку правятся: настройки сайта (название, телефон, адрес), товары, категории, бренды, акции, блог, тарифы доставки, пункты самовывоза, заказы, возвраты.

---

## Безопасность

- CSRF на всех формах и POST-эндпоинтах
- API по умолчанию — `IsAuthenticated`; публичные эндпоинты явно `AllowAny`
- DRF throttling: 60/мин анон, 200/мин user
- Чат: 60 сообщений/час на сессию
- Транзакционная защита при создании заказа (`select_for_update`)
- HTTPS/HSTS/Secure cookies включаются автоматически при `DEBUG=False`
- Пароли валидируются Django `AUTH_PASSWORD_VALIDATORS`
- `.env` в `.gitignore` — секреты не попадают в репозиторий
- AI-чат работает оффлайн (через Ollama) — никакие запросы пользователей не уходят во внешние сервисы

---

## Типовые проблемы

### `[ollama] Ollama CLI not found in PATH`
Ollama не установлена или терминал не перезапущен. Установи с [ollama.com/download](https://ollama.com/download), затем **открой новый терминал**.

### `[ollama] daemon did not become ready within 30s`
Запусти `ollama serve` вручную в отдельном терминале и посмотри ошибку. Часто помогает перезагрузка.

### Чат отвечает «Ассистент временно недоступен»
1. Проверь, что Ollama работает: `curl http://localhost:11434/api/tags`
2. Проверь, что модель скачана: `ollama list`
3. Включи `DEBUG=True` в `.env` — в ответе чата появится детализация ошибки
4. Смотри логи в консоли `runserver` — полный traceback там

### Поиск товаров не находит кириллицу
Убедись, что `shop/apps.py` правильно применился (там патч SQLite `LOWER` для кириллицы). Перезапусти `runserver`.

### Модель медленно отвечает
- На CPU модели 3B+ дают ~5–15 токенов/сек — это нормально.
- Переключись на `llama3.2:1b` для скорости ценой качества.
- Если есть NVIDIA GPU — Ollama автоматически её использует, проверь `ollama ps`.

---

## Лицензия

Проект разработан для учебных и коммерческих целей.
