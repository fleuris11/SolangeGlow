# syntax=docker/dockerfile:1

FROM python:3.12-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# GeoDjango needs GDAL, GEOS and PROJ; gettext compiles the translations;
# ffmpeg converts videos and voice notes.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gdal-bin binutils gettext ffmpeg \
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

# --- Production: dependencies, static files and translations prepared apart -----
FROM base AS prod-build
COPY requirements /tmp/requirements
RUN python -m venv /opt/venv && /opt/venv/bin/pip install -r /tmp/requirements/prod.txt
COPY . /app
# These values only let the settings load during the build: nothing keeps them.
RUN DJANGO_SETTINGS_MODULE=config.settings.prod \
    DJANGO_SECRET_KEY=image-build-only-0123456789-0123456789-0123456789 \
    INTERNAL_API_TOKEN=image-build-only-0123456789-0123456789-0123456789 \
    DJANGO_ALLOWED_HOSTS=build SITE_URL=https://build IDENTITY_VAULT_KEY=build \
    AWS_STORAGE_BUCKET_NAME=build DATABASE_URL=postgis://build@localhost/build \
    sh -c "/opt/venv/bin/python manage.py collectstatic --noinput \
    && /opt/venv/bin/python manage.py compilemessages --ignore=.venv --verbosity 0"

FROM base AS prod
COPY --from=prod-build /opt/venv /opt/venv
COPY --from=prod-build --chown=app:app /app /app
ENV DJANGO_SETTINGS_MODULE=config.settings.prod \
    PATH=/opt/venv/bin:$PATH
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD ["python", "-c", "import urllib.request as u; u.urlopen(u.Request('http://localhost:8000/api/v1/health?deep=1', headers={'Host': 'backend'}), timeout=8)"]
CMD ["gunicorn", "config.asgi:application", "-c", "docker/gunicorn.conf.py"]
