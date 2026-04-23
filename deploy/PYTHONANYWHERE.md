# Деплой Paperly на PythonAnywhere

Пошаговая инструкция для размещения проекта на [pythonanywhere.com](https://www.pythonanywhere.com).

## Что работает / что нет

| Функция | Free | Paid ($5/мес) |
|---|---|---|
| Django + SQLite + админка | ✅ | ✅ |
| Static через WhiteNoise | ✅ | ✅ |
| Media (картинки товаров) | ✅ | ✅ |
| Email через SMTP Yandex | ✅ | ✅ |
| Celery / Redis | ❌ | ✅ (always-on tasks) |
| Кастомный домен | ❌ | ✅ |

Чат-виджет не требует внешних API — все ответы зашиты в JS, подборки товаров тянутся из собственного `/api/products/`. Работает на любом тарифе.

## Шаг 1. Подготовить репозиторий локально

```bash
cd C:\Users\Anton\Desktop\moneyV2

# Убедитесь, что всё закоммичено
git status
git add -A
git commit -m "Prepare for PythonAnywhere deployment"
git push
```

## Шаг 2. Создать аккаунт и веб-приложение на PA

1. Зарегистрируйтесь на [pythonanywhere.com](https://www.pythonanywhere.com) (тариф «Beginner» — бесплатный, этого хватит)
2. Откройте вкладку **Web** → **Add a new web app**
3. Domain: `ВАШ_USERNAME.pythonanywhere.com` (нажмите Next)
4. Framework: выберите **Manual configuration** (не Django — чтобы потом всё настроить вручную)
5. Python version: **Python 3.11** (или 3.10, если 3.11 недоступен)
6. Нажмите Next — PA создаст заглушку

## Шаг 3. Клонировать проект через Bash-консоль PA

На PA откройте вкладку **Consoles** → **Bash**:

```bash
# В домашнем каталоге /home/USERNAME/
git clone https://github.com/ВАШ_GITHUB/paperly.git
# если репозиторий приватный, используйте HTTPS + personal access token
# или настройте SSH-ключи (Account → SSH keys)

cd paperly
ls
# должны увидеть: backend/  README.md  deploy/  .gitignore
```

## Шаг 4. Виртуальное окружение

```bash
cd ~/paperly
mkvirtualenv --python=python3.11 paperly-venv
# После создания PA автоматически активирует его.
# В будущем: `workon paperly-venv` чтобы активировать.

cd backend
pip install -r requirements-prod.txt
```

## Шаг 5. Настроить `.env`

```bash
nano ~/paperly/backend/.env
```

Вставьте содержимое (поменяйте значения):

```env
DEBUG=False
SECRET_KEY=ваш-случайный-секретный-ключ-минимум-50-символов
ALLOWED_HOSTS=ВАШ_USERNAME.pythonanywhere.com
CSRF_TRUSTED_ORIGINS=https://ВАШ_USERNAME.pythonanywhere.com

# Email (если нужен сброс пароля)
EMAIL_HOST=smtp.yandex.ru
EMAIL_PORT=465
EMAIL_USE_SSL=True
EMAIL_HOST_USER=paperly.work@yandex.ru
EMAIL_HOST_PASSWORD=jrizrwwkbtcgbljp
DEFAULT_FROM_EMAIL=paperly.work@yandex.ru
```

Сохранить: **Ctrl+O**, Enter, **Ctrl+X**.

Сгенерировать SECRET_KEY если нужен:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## Шаг 6. Миграции, seed, collectstatic, суперпользователь

```bash
cd ~/paperly/backend
workon paperly-venv   # если ещё не активирован

python manage.py migrate
python manage.py seed_demo_data       # если хотите демо-контент
python manage.py createsuperuser       # создаст админа
python manage.py collectstatic --noinput
```

## Шаг 7. Настроить WSGI и пути на вкладке Web

На PA **Web** → вкладка с вашим app:

### 7.1. Source code
```
/home/ВАШ_USERNAME/paperly/backend
```

### 7.2. Working directory
```
/home/ВАШ_USERNAME/paperly/backend
```

### 7.3. Virtualenv
```
/home/ВАШ_USERNAME/.virtualenvs/paperly-venv
```

### 7.4. WSGI file — нажмите на ссылку, откроется редактор
Удалите всё, вставьте (поменяйте USERNAME):

```python
import os
import sys

from dotenv import load_dotenv

USERNAME = "ВАШ_USERNAME"
PROJECT_DIR = f"/home/{USERNAME}/paperly/backend"

if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

# Загружаем .env
load_dotenv(f"{PROJECT_DIR}/.env")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "paperly_backend.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

Save.

### 7.5. Static files mapping
В разделе **Static files**:

| URL | Directory |
|---|---|
| `/static/` | `/home/ВАШ_USERNAME/paperly/backend/staticfiles` |
| `/media/` | `/home/ВАШ_USERNAME/paperly/backend/media` |

*(static можно и без этого — WhiteNoise их раздаёт — но явное mapping быстрее)*

## Шаг 8. Reload и проверка

Нажмите большую зелёную кнопку **Reload ВАШ_USERNAME.pythonanywhere.com** вверху.

Откройте `https://ВАШ_USERNAME.pythonanywhere.com` — должна отобразиться главная Paperly.

### Проверьте:
- `/catalog/` — каталог рендерится
- `/admin/` — админка грузится (войдите суперпользователем)
- `/product/?id=1` — карточка товара
- `/cart/` — корзина

### Если ошибка 500:
Смотрите лог: **Web → Error log** — файл `username.pythonanywhere.com.error.log`. Там увидите стек трейса.

Частые проблемы:
- **DisallowedHost** — проверьте `ALLOWED_HOSTS` в `.env`
- **SECRET_KEY is required** — проверьте, что `.env` есть и `load_dotenv` отрабатывает
- **Static не грузится** — проверьте `STATIC_ROOT` и запуск `collectstatic`
- **Database locked** — SQLite на PA работает, но не для heavy traffic; для прода лучше MySQL/Postgres

## Шаг 9. После deploy — обновления кода

```bash
workon paperly-venv
cd ~/paperly/backend
git pull
pip install -r requirements-prod.txt   # если requirements менялись
python manage.py migrate
python manage.py collectstatic --noinput
# потом → Web tab → Reload
```

## Отключение функций, несовместимых с PA

### Newsletter через Celery
Celery на free нет. Мы не используем Celery для отправки — всё через обычный `send_mail`. Работает синхронно.

## MySQL вместо SQLite (опционально, paid-тариф)

Если планируете хоть какой-то трафик — перейдите на MySQL:

```python
# settings.py
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "USERNAME$paperly",
        "USER": "USERNAME",
        "PASSWORD": os.environ["DB_PASSWORD"],
        "HOST": "USERNAME.mysql.pythonanywhere-services.com",
    }
}
```

На PA → **Databases** → создать БД `paperly` → добавить пароль в `.env`.

## Кастомный домен (paid-тариф)

1. На PA → Web → Domain → ввести ваш домен (например, `paperly.ru`)
2. Скопировать CNAME target
3. В DNS вашего провайдера прописать CNAME, указывающий на PA
4. PA автоматически выдаст Let's Encrypt сертификат

Готово!
