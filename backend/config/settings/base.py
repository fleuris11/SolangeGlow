"""Base settings shared by every environment.

Every value that changes between environments is read from environment variables
(see `.env.example` at the repository root). Business parameters (deadlines, fees,
commissions) never live here: they are stored in `core.PlatformSetting`.
"""

from datetime import timedelta
from pathlib import Path

import environ
from django.templatetags.static import static
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR.parent / ".env", overwrite=False)

# --- Security -----------------------------------------------------------------

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

# --- Applications -------------------------------------------------------------

DJANGO_APPS = [
    # Unfold must come before django.contrib.admin.
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    # Daphne makes `runserver` serve ASGI (HTTP + WebSocket).
    "daphne",
    # modeltranslation must come before django.contrib.admin.
    "modeltranslation",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "drf_spectacular",
    "channels",
    "django_celery_beat",
    "phonenumber_field",
    "storages",
]

LOCAL_APPS = [
    "apps.core",
    "apps.accounts",
    "apps.pros",
    "apps.social",
    "apps.messaging",
    "apps.shop",
    "apps.payments",
    "apps.selection_france",
    "apps.academy",
    "apps.booking",
    "apps.gamification",
    "apps.ads",
    "apps.moderation",
    "apps.notifications",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
            ],
        },
    },
]

# --- Database (PostgreSQL + PostGIS) ------------------------------------------

DATABASES = {
    "default": env.db_url(
        "DATABASE_URL",
        engine="django.contrib.gis.db.backends.postgis",
    ),
}
DATABASES["default"]["ENGINE"] = "django.contrib.gis.db.backends.postgis"
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DATABASE_CONN_MAX_AGE", default=60)
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Cache (Redis) ------------------------------------------------------------

REDIS_URL = env("REDIS_URL", default="redis://redis:6379/0")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("CACHE_URL", default=REDIS_URL),
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
        "KEY_PREFIX": "sg",
    }
}

# --- Authentication -----------------------------------------------------------

AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = ["apps.accounts.backends.PhoneOrEmailBackend"]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

PHONENUMBER_DB_FORMAT = "E164"
PHONENUMBER_DEFAULT_REGION = env("PHONENUMBER_DEFAULT_REGION", default="BJ")

# --- Internationalisation -----------------------------------------------------

LANGUAGE_CODE = "fr"
LANGUAGES = [
    ("fr", _("French")),
    ("en", _("English")),
    ("sk", _("Slovak")),
]
LOCALE_PATHS = [BASE_DIR / "locale"]
USE_I18N = True
USE_TZ = True
TIME_ZONE = "Europe/Paris"

MODELTRANSLATION_DEFAULT_LANGUAGE = "fr"
MODELTRANSLATION_LANGUAGES = ("fr", "en", "sk")
MODELTRANSLATION_FALLBACK_LANGUAGES = ("fr", "en")

# --- Static and media files ---------------------------------------------------

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# --- Django REST Framework ----------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "apps.core.api.pagination.DefaultCursorPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.core.api.exceptions.exception_handler",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": env("API_THROTTLE_ANON", default="120/minute"),
        "user": env("API_THROTTLE_USER", default="600/minute"),
    },
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Solange Glow API",
    "DESCRIPTION": "Public API of the Solange Glow platform.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": r"/api/v[0-9]+",
    "COMPONENT_SPLIT_REQUEST": True,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env.int("JWT_ACCESS_MINUTES", default=15)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env.int("JWT_REFRESH_DAYS", default=30)),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "SIGNING_KEY": env("JWT_SIGNING_KEY", default="") or SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# --- Channels -----------------------------------------------------------------

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [env("CHANNELS_REDIS_URL", default=REDIS_URL)]},
    }
}

# --- Celery -------------------------------------------------------------------

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default=REDIS_URL)
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_TIME_LIMIT = env.int("CELERY_TASK_TIME_LIMIT", default=300)
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# --- Platform settings cache ----------------------------------------------------

PLATFORM_SETTINGS_CACHE_TIMEOUT = env.int("PLATFORM_SETTINGS_CACHE_TIMEOUT", default=300)

# --- Logging ------------------------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "{asctime} {levelname} {name} {message}", "style": "{"},
    },
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "simple"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
    "loggers": {
        "django.db.backends": {"level": "WARNING"},
    },
}

# --- Admin (Unfold) -----------------------------------------------------------

UNFOLD = {
    "SITE_TITLE": "Solange Glow",
    "SITE_HEADER": "Solange Glow",
    "SITE_SUBHEADER": _("Back office"),
    "SITE_SYMBOL": "spa",
    "SITE_ICON": lambda request: static("admin/brand/logo.png"),
    "SITE_FAVICONS": [
        {
            "rel": "icon",
            "sizes": "32x32",
            "type": "image/png",
            "href": lambda request: static("admin/brand/favicon-32.png"),
        },
    ],
    "SHOW_LANGUAGES": True,
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": False,
    "BORDER_RADIUS": "14px",
    # Hibiscus scale built around the brand red #C8102E (600), see solange-design.
    "COLORS": {
        "base": {
            "50": "oklch(98.2% 0.009 34)",
            "100": "oklch(95.5% 0.018 0)",
            "200": "oklch(90.1% 0.021 359)",
            "300": "oklch(82.5% 0.035 345)",
            "400": "oklch(66.7% 0.05 340)",
            "500": "oklch(52.7% 0.07 335)",
            "600": "oklch(44.5% 0.075 335)",
            "700": "oklch(36.5% 0.08 335)",
            "800": "oklch(29.4% 0.085 335)",
            "900": "oklch(26.2% 0.08 336)",
            "950": "oklch(17.2% 0.036 339)",
        },
        "primary": {
            "50": "oklch(97.1% 0.014 12)",
            "100": "oklch(93.6% 0.032 12)",
            "200": "oklch(88.5% 0.062 14)",
            "300": "oklch(80.8% 0.114 16)",
            "400": "oklch(71.1% 0.166 19)",
            "500": "oklch(63.7% 0.208 23)",
            "600": "oklch(53% 0.207 22.3)",
            "700": "oklch(47.5% 0.19 24)",
            "800": "oklch(40.6% 0.16 24)",
            "900": "oklch(35.5% 0.13 22)",
            "950": "oklch(25.8% 0.09 20)",
        },
        "font": {
            "subtle-light": "var(--color-base-500)",
            "subtle-dark": "var(--color-base-400)",
            "default-light": "var(--color-base-700)",
            "default-dark": "var(--color-base-200)",
            "important-light": "var(--color-base-900)",
            "important-dark": "var(--color-base-100)",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": [
            {
                "title": _("Platform"),
                "separator": True,
                "items": [
                    {
                        "title": _("Countries"),
                        "icon": "public",
                        "link": reverse_lazy("admin:core_country_changelist"),
                    },
                    {
                        "title": _("Currencies"),
                        "icon": "payments",
                        "link": reverse_lazy("admin:core_currency_changelist"),
                    },
                    {
                        "title": _("Platform settings"),
                        "icon": "tune",
                        "link": reverse_lazy("admin:core_platformsetting_changelist"),
                    },
                    {
                        "title": _("Feature flags"),
                        "icon": "toggle_on",
                        "link": reverse_lazy("admin:core_featureflag_changelist"),
                    },
                ],
            },
            {
                "title": _("Accounts"),
                "separator": True,
                "items": [
                    {
                        "title": _("Users"),
                        "icon": "group",
                        "link": reverse_lazy("admin:accounts_user_changelist"),
                    },
                    {
                        "title": _("Groups"),
                        "icon": "shield_person",
                        "link": reverse_lazy("admin:auth_group_changelist"),
                    },
                ],
            },
        ],
    },
}
