"""
WSGI-файл для PythonAnywhere.

Скопируйте содержимое в файл, который PA автоматически создаёт:
    /var/www/<USERNAME>_pythonanywhere_com_wsgi.py

Заменив:
    USERNAME — ваш логин PA
    PROJECT_DIR — путь до папки backend/ проекта на PA
                  (обычно /home/USERNAME/paperly/backend)

После правки нажмите «Reload» на Web tab.
"""

import os
import sys

# ───── 1. Пути проекта ─────
USERNAME = "YOUR_USERNAME"
PROJECT_DIR = f"/home/{USERNAME}/paperly/backend"

if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

# ───── 2. Environment variables ─────
# Всё, что нужно: SECRET_KEY, DEBUG=False, ALLOWED_HOSTS, email-креды.
# Лучше их задать через .env рядом с settings.py — python-dotenv подхватит.
# Но на всякий случай можно и здесь:
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "paperly_backend.settings")

# ───── 3. Django WSGI application ─────
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
