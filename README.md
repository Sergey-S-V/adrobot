## Запуск

Нужен Docker. Из папки проекта:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
# Задайте ADROBOT_KEITARO_BASE_URL и ADROBOT_KEITARO_API_KEY в .env.
docker compose up -d --build --wait
```

Откройте http://127.0.0.1:3000. Для новой кампании нажмите «Создать кампанию»; ID кампании нужен только для открытия существующей через Fetch. Данные сохраняются в Docker volume.

Миграция применяется при запуске. Вручную, при работающей PostgreSQL:

```powershell
uv sync --locked --dev
uv run --env-file .env alembic -c backend/alembic.ini upgrade head
```