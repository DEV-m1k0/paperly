#!/usr/bin/env bash
# Скрипт сборки для Render.com — выполняется при каждом deploy.
# Render запускает его автоматически после `pip install`.

set -o errexit   # останавливаем сборку при любой ошибке

# 1. Устанавливаем production-зависимости
pip install -r backend/requirements-prod.txt

# 2. Собираем static-файлы (WhiteNoise обслужит их)
cd backend
python manage.py collectstatic --noinput --clear

# 3. Применяем миграции к Postgres
python manage.py migrate --noinput

# 4. Наполняем демо-данными ТОЛЬКО если БД пустая.
#    В проде эта команда идемпотентна — повторный запуск ничего не сломает.
python manage.py seed_demo_data || echo "seed_demo_data skipped (already seeded)"

echo "✅ Build complete"
