# Деплой Paperly на Render.com

Всё готово к деплою через **Blueprint** (render.yaml). От тебя требуется только
зарегистрироваться в Render и заполнить 3 переменных окружения — остальное
Render сделает автоматически.

## Что будет создано

- **Web-сервис** Django + gunicorn + WhiteNoise (free tier, 750 ч/мес)
- **Postgres database** paperly-db (free, 256 MB)
- **Автодеплой** при push в `master`
- **HTTPS** бесплатно (Let's Encrypt, выдаётся Render'ом)
- **Cold start** 15-30 сек после 15 мин неактивности (ограничение free)

---

## Шаг 1. Запушить изменения на GitHub (1 мин)

Я уже подготовил все нужные файлы (`build.sh`, `render.yaml`, `requirements-prod.txt`
и правки в `settings.py`). Осталось закоммитить и запушить:

```bash
cd C:\Users\Anton\Desktop\moneyV2
git add -A
git commit -m "Prepare for Render deployment"
git push
```

---

## Шаг 2. Создать Blueprint на Render (3 мин)

1. Зайди на [render.com](https://render.com) → **Get Started**
2. Войди через **GitHub** → разрешить доступ к репозиторию `paperly`
3. Dashboard → **New +** → **Blueprint**
4. Connect репозиторий `DEV-m1k0/paperly`
5. Render автоматически найдёт `render.yaml` и предложит создать:
   - `paperly` (web service)
   - `paperly-db` (Postgres)
6. Нажми **Apply**

Render начнёт первый build (3-5 мин). Пока идёт — переходи к шагу 3.

---

## Шаг 3. Задать секретные переменные (3 мин)

В `render.yaml` помечены переменные как `sync: false` — Render не получит их
автоматически, их нужно задать вручную в dashboard.

В Render dashboard → **paperly** (web service) → вкладка **Environment**:

| Key | Value | Комментарий |
|---|---|---|
| `EMAIL_HOST_USER` | `your-email@yandex.ru` | Твой SMTP-логин |
| `EMAIL_HOST_PASSWORD` | `jrizrwwkbtcgbljp` | app-password Yandex |
| `DEFAULT_FROM_EMAIL` | `your-email@yandex.ru` | Отправитель |

Нажми **Save Changes** — Render пересоберёт сервис автоматически.

> **Как получить Yandex app-password**: [id.yandex.ru/security](https://id.yandex.ru/security) → Пароли приложений → создать → «Почта». Обычный пароль от аккаунта не подойдёт, Yandex требует именно app-password для SMTP.

---

## Шаг 4. Дождаться первого деплоя и проверить (5 мин)

На странице сервиса `paperly` → вкладка **Logs**:

Должен пройти build:
```
==> Running './build.sh'
Collecting package metadata (current_repodata.json): ...done
Successfully installed Django-4.2 ... gunicorn-23.0.0 ...
✅ Build complete
==> Starting service with 'cd backend && gunicorn paperly_backend.wsgi:application'
[2026-04-22 ...] Listening at: http://0.0.0.0:10000
```

Затем в dashboard покажется `Live` и URL:
```
https://paperly.onrender.com
```

Открой — должна появиться главная Paperly.

### Что проверить:
- `/catalog/` — каталог рендерится
- `/product/?id=1` — карточка товара
- `/admin/` — админка (см. шаг 5 чтобы войти)
- **Чат** (значок справа снизу) — должен открыться, кнопка «Подобрать товар» → выбор категории → показ карточек товаров

---

## Шаг 5. Создать суперпользователя (1 мин)

Render → **paperly** → вкладка **Shell** (доступна на paid-тарифе).

На free-тарифе без Shell — `seed_demo_data` уже создаёт админа (`admin`/`admin12345`). Если хочется своего — можно так:

Вариант A (через локальный подключение к Render Postgres):

```bash
# На локальной машине:
cd backend
export DATABASE_URL="postgres://...<твой URL от Render>..."
.venv/Scripts/python.exe manage.py createsuperuser
# Укажи логин/пароль
unset DATABASE_URL
```

DATABASE_URL берётся на Render → **paperly-db** → вкладка **Info** → External Database URL.

Вариант B — проще, если Shell недоступен: временно положить в `.env.example`
management-команду, задеплоить, удалить, задеплоить.

Я могу написать short helper-management-command если нужно — скажи.

---

## Первый deploy готов!

После этого каждый `git push` в master будет автоматически пересобирать и
деплоить сайт.

```bash
git add -A && git commit -m "..." && git push
# Render увидит push → rebuild → новая версия live через 3-5 мин
```

---

## Известные ограничения free-тарифа

### 1. Sleep после 15 мин
Первый запрос после паузы = 15-30 сек холодный старт. Это **нормально** для free.
Чтобы избежать — поставь keep-alive ping через UptimeRobot (бесплатно) на URL
`https://paperly.onrender.com/`.

### 2. Postgres free — 90 дней
Render даёт Postgres бесплатно на 90 дней, потом нужно удалять или платить $7/мес.
Альтернативы:
- **Supabase** — бесплатно навсегда, 500 MB. Нужно сменить `DATABASE_URL`
- **Neon** — бесплатно навсегда, 3 GB. Тоже просто смена URL

### 3. Media-файлы не persist
При перезапуске сервиса загруженные в админке изображения товаров **теряются**.
`collectstatic` и `seed_demo_data` их перекладывают заново при каждой сборке,
но пользовательские загрузки — исчезают. Решение:
- **Cloudinary** (бесплатно 25 GB) — медиа в облаке
- **Supabase Storage** — бесплатно 1 GB
- Пока на демо это не критично — seed всегда восстановит состояние.

---

## Если что-то сломалось

### Build не проходит
`Logs` вкладка → найди красную строку с `ERROR`. Типичные:
- `ModuleNotFoundError: dj_database_url` — проверь что `requirements-prod.txt` в репо
- `permission denied: ./build.sh` — сделай `chmod +x build.sh` локально и закоммить
- `psycopg2 installation fails` — уже используем `psycopg2-binary`, не должно быть

### Сервис запустился, но 500
`Logs` вкладка → смотри последний traceback.
- `DisallowedHost` — проверь `ALLOWED_HOSTS` содержит твой `.onrender.com` домен
- `no such table` — миграции не применились; посмотри build log, есть ли `migrate` ошибка

### Что-то ещё непонятное
Скажи мне — посмотрим вместе.

---

## Переход на кастомный домен (опционально)

1. Купить домен у любого регистратора (nic.ru, reg.ru)
2. Render → **paperly** → **Settings** → **Custom Domains** → **Add**
3. Ввести домен → Render даст CNAME
4. В DNS-провайдере домена создать CNAME-запись → `paperly.onrender.com`
5. Render автоматически выдаст Let's Encrypt сертификат за 5-30 мин

Стоимость: только регистрация домена (~200₽/год на `.ru`, от $10/год на `.com`).
