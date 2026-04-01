import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

# ─── Security ────────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-change-me-in-production')
DEBUG = os.environ.get('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1,0.0.0.0').split(',')

ADMIN_URL = os.environ.get('ADMIN_URL', 'admin')

# ─── Applications ─────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',
    'django.contrib.sites',
    'django.contrib.redirects',
    # Project apps
    'apps.users',
    'apps.blog',
    'apps.vendors',
    'apps.news',
    'apps.pages',
    'apps.newsletter',
    'apps.ads',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.contrib.redirects.middleware.RedirectFallbackMiddleware',
    'csp.middleware.CSPMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.pages.context_processors.footer_pages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ─── Auth ─────────────────────────────────────────────────────────────────────
AUTH_USER_MODEL = 'users.User'
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ─── Database ─────────────────────────────────────────────────────────────────
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        'OPTIONS': {'timeout': 20},
    }
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SITE_ID = 1

# ─── Internationalization ─────────────────────────────────────────────────────
LANGUAGE_CODE = 'ru'
TIME_ZONE = 'Asia/Ho_Chi_Minh'
USE_I18N = True
USE_TZ = True

# ─── Static & Media ───────────────────────────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
    BASE_DIR / 'bot_eat_blog' / 'website' / 'static',
]
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ─── Email (Mailjet) ──────────────────────────────────────────────────────────
EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend'
)
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'in-v3.mailjet.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('MAILJET_API_KEY', '')
EMAIL_HOST_PASSWORD = os.environ.get('MAILJET_SECRET_KEY', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'КликМи <noreply@clikme.ru>')

# ─── AI / GitHub Models ───────────────────────────────────────────────────────
AI_PROVIDER = os.environ.get('AI_PROVIDER', 'github')
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')

# ─── Telegram ─────────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHANNEL_ID = os.environ.get('TELEGRAM_CHANNEL_ID', '')

# ─── Affiliate ────────────────────────────────────────────────────────────────
TRIP_ALLIANCE_ID = os.environ.get('TRIP_ALLIANCE_ID', '6229959')
TRIP_SID = os.environ.get('TRIP_SID', '192412375')

# ─── Mollie ──────────────────────────────────────────────────────────────────
MOLLIE_API_KEY = os.environ.get('MOLLIE_API_KEY', '')
MOLLIE_WEBHOOK_URL = os.environ.get('MOLLIE_WEBHOOK_URL', '')

# ─── Cache (файловый, без Redis) ──────────────────────────────────────────────
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': BASE_DIR / '.cache',
    }
}

# ─── Security headers (только в production) ───────────────────────────────────
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

    # CSP в режиме Report-Only — логирует нарушения, ничего не блокирует.
    # После анализа логов заменить на Content-Security-Policy.
    SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'
    CSP_REPORT_ONLY = True
    CSP_DEFAULT_SRC = ("'self'",)
    CSP_SCRIPT_SRC = (
        "'self'",
        "'unsafe-inline'",    # Django admin + Яндекс.Метрика
        "https://mc.yandex.ru",
        "https://cdnjs.cloudflare.com",
    )
    CSP_STYLE_SRC = (
        "'self'",
        "'unsafe-inline'",    # Tailwind inline styles
        "https://fonts.googleapis.com",
        "https://cdnjs.cloudflare.com",
    )
    CSP_FONT_SRC = (
        "'self'",
        "https://fonts.gstatic.com",
    )
    CSP_IMG_SRC = (
        "'self'",
        "data:",
        "https:",             # внешние картинки новостей
    )
    CSP_CONNECT_SRC = (
        "'self'",
        "https://mc.yandex.ru",
    )
    CSP_FRAME_SRC = ("'none'",)

X_FRAME_OPTIONS = 'DENY'

# ─── Sentry ───────────────────────────────────────────────────────────────────
SENTRY_DSN = os.environ.get('SENTRY_DSN', '')
if SENTRY_DSN:
    import sentry_sdk
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment='production' if not DEBUG else 'development',
        traces_sample_rate=0.2,   # 20% транзакций для performance monitoring
        send_default_pii=False,
    )

# ─── Logging ──────────────────────────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
        },
    },
    'root': {
        'handlers': ['file'],
        'level': 'ERROR',
    },
}
