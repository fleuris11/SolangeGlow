# syntax=docker/dockerfile:1

FROM python:3.12-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# GeoDjango needs GDAL, GEOS and PROJ; gettext compiles the translations.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gdal-bin binutils gettext \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system app && useradd --system --gid app --home-dir /app app
WORKDIR /app

COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN sed -i 's/\r$//' /usr/local/bin/entrypoint.sh && chmod +x /usr/local/bin/entrypoint.sh
ENTRYPOINT ["entrypoint.sh"]

# --- Development image (code mounted from the host) -----------------------------
FROM base AS dev
COPY requirements /tmp/requirements
RUN pip install -r /tmp/requirements/dev.txt
ENV DJANGO_SETTINGS_MODULE=config.settings.dev
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# --- Production image -----------------------------------------------------------
FROM base AS prod
COPY requirements /tmp/requirements
RUN pip install -r /tmp/requirements/prod.txt
COPY --chown=app:app . /app
ENV DJANGO_SETTINGS_MODULE=config.settings.prod
RUN DJANGO_SECRET_KEY=build DATABASE_URL=postgis://build@localhost/build \
    python manage.py collectstatic --noinput \
    && python manage.py compilemessages --ignore=.venv
USER app
EXPOSE 8000
CMD ["gunicorn", "config.asgi:application", "-k", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", "--workers", "3"]
