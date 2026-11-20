FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_LINK_MODE=copy
WORKDIR /app
RUN pip install --no-cache-dir uv==0.13.5
COPY pyproject.toml uv.lock ./
COPY backend ./backend
RUN uv sync --locked --no-dev --no-editable && useradd --uid 10001 --create-home adrobot
ENV PATH="/app/.venv/bin:$PATH"
USER adrobot
EXPOSE 8000
CMD ["uvicorn", "adrobot.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
