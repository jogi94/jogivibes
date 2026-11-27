FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

RUN pip install --no-cache-dir poetry==2.4.1

COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-root --no-interaction

COPY . .

# Collect static assets at build time. Runtime settings are supplied by Cloud Run.
RUN DJANGO_DEBUG=true \
    DJANGO_SECRET_KEY=build-only-key \
    poetry run python manage.py collectstatic --noinput

EXPOSE 8080

CMD ["sh", "-c", "poetry run gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8080} --workers 2 --timeout 120"]
