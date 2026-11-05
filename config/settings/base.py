import tomllib
from pathlib import Path

import structlog
from csp.constants import NONE, SELF
from decouple import Csv, config

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Jedno źródło wersji: [project].version w pyproject.toml (aktualizowane przez /release-docs).
with open(BASE_DIR / "pyproject.toml", "rb") as f:
    APP_VERSION = tomllib.load(f)["project"]["version"]

SECRET_KEY = config("SECRET_KEY", default="django-insecure-dev-only-change-in-prod")

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",  # TrigramSimilarity w wyszukiwarce bloga
    "django.contrib.sitemaps",
]

THIRD_PARTY_APPS = [
    "taggit",
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_spectacular",
    "corsheaders",
    "django_prometheus",
    "axes",
    "django_otp",
    "django_otp.plugins.otp_totp",
    "django_otp.plugins.otp_static",
]

LOCAL_APPS = [
    "apps.core",
    "apps.users",
    "apps.cookies",
    "apps.cv",
    "apps.blog",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

AUTH_USER_MODEL = "users.User"

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "csp.middleware.CSPMiddleware",
    "apps.core.middleware.RequestContextMiddleware",
    "apps.cookies.middleware.CookieConsentMiddleware",
    "axes.middleware.AxesMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

CDN_JSDELIVR = "https://cdn.jsdelivr.net"

CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": [SELF],
        "script-src": [SELF, CDN_JSDELIVR],
        "style-src": [SELF, CDN_JSDELIVR],
        "img-src": [SELF, "data:"],
        "font-src": [SELF, CDN_JSDELIVR],
        "connect-src": [SELF],
        "object-src": [NONE],
        "base-uri": [SELF],
        "frame-ancestors": [NONE],
    },
}

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Ścieżka panelu admina z .env — nie zabezpieczenie (od tego są axes + OTP), tylko mniej botów w logach.
# Normalizacja do postaci "sciezka/" niezależnie od tego, czy w .env jest "/sciezka", "sciezka/" czy "sciezka".
ADMIN_URL = config("ADMIN_URL", default="admin/").strip("/") + "/"

AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1
# Lista zagnieżdżona = kombinacja (to konto Z TEGO IP). Płaska ["username", "ip_address"] blokowałaby
# osobno po loginie LUB po IP — każdy znający login mógłby zablokować właściciela z dowolnego adresu.
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
# Domyślnie axes szuka loginu pod USERNAME_FIELD ("email"), a formularz admina i authenticate()
# przekazują go jako "username" — bez tego axes zapisuje login jako None i ignoruje go przy blokadzie.
AXES_USERNAME_FORM_FIELD = "username"

TAGGIT_CASE_INSENSITIVE = True

# Blog — komentarze publikowane od razu, właściciel dostaje e-mail z linkiem do moderacji w adminie.
BLOG_POSTS_PER_PAGE = 5
BLOG_COMMENT_RATE_LIMIT = 10  # komentarzy na godzinę z jednego IP
BLOG_COMMENT_NOTIFY_EMAILS = config("BLOG_COMMENT_NOTIFY_EMAILS", default="", cast=Csv())

# Poczta wychodząca (powiadomienia o komentarzach). Bez EMAIL_HOST maile lądują w logach (console).
# testing.py nadpisuje backend na locmem.
EMAIL_HOST = config("EMAIL_HOST", default="")
EMAIL_BACKEND = (
    "django.core.mail.backends.smtp.EmailBackend" if EMAIL_HOST else "django.core.mail.backends.console.EmailBackend"
)
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="webmaster@localhost")

LANGUAGE_CODE = "pl-pl"
TIME_ZONE = "Europe/Warsaw"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "1000/hour",
    },
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "API",
    "VERSION": APP_VERSION,
    "SERVE_INCLUDE_SCHEMA": False,
}

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processors": [
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.processors.JSONRenderer(),
            ],
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
