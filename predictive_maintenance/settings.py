"""
Django settings for predictive_maintenance project.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env if present
load_dotenv(BASE_DIR / '.env')

# Quick-start development settings - unsuitable for production
SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-ai-predictive-maintenance-system-key-change-in-prod-2026'
)

DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = ['*']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third party
    'corsheaders',
    # Local app
    'telemetry.apps.TelemetryConfig',
]

try:
    import whitenoise
    HAVE_WHITENOISE = True
except ImportError:
    HAVE_WHITENOISE = False

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    *(['whitenoise.middleware.WhiteNoiseMiddleware'] if HAVE_WHITENOISE else []),
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    # CSRF disabled for /api/ endpoints via csrf_exempt in views
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'predictive_maintenance.urls'

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
            ],
        },
    },
]

WSGI_APPLICATION = 'predictive_maintenance.wsgi.application'
ASGI_APPLICATION = 'predictive_maintenance.asgi.application'

# Database configuration
# Defaults to SQLite for immediate local operation; seamlessly switches to PostgreSQL if DATABASE_URL is set
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    try:
        import urllib.parse
        url = urllib.parse.urlparse(DATABASE_URL)
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': url.path[1:] if url.path else 'maintenance',
                'USER': url.username,
                'PASSWORD': url.password,
                'HOST': url.hostname,
                'PORT': url.port or 5432,
                'OPTIONS': {
                    'sslmode': 'require' if 'neon.tech' in (url.hostname or '') or 'render.com' in (url.hostname or '') else 'prefer'
                }
            }
        }
    except Exception as exc:
        print(f"[Warning] Failed parsing DATABASE_URL: {exc}. Falling back to SQLite.")
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': BASE_DIR / 'db.sqlite3',
            }
        }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

if HAVE_WHITENOISE:
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
        },
    }

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CSRF & CORS configuration
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = [
    'https://*.onrender.com',
    'https://*.railway.app',
    'https://*.up.railway.app',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]

# ---------------------------------------------------------------------------
# Predictive Maintenance Fleet & Alert Configurations
# ---------------------------------------------------------------------------
_raw_machines = os.environ.get('MONITORED_MACHINES', 'M01,M02,M03')
MONITORED_MACHINES = [m.strip() for m in _raw_machines.split(',') if m.strip()]

ALERT_RISK_THRESHOLD = int(os.environ.get('ALERT_RISK_THRESHOLD', '75'))
ALERT_COOLDOWN_MINUTES = int(os.environ.get('ALERT_COOLDOWN_MINUTES', '30'))
EMAIL_ALERTS_ENABLED = os.environ.get('EMAIL_ALERTS_ENABLED', 'true').lower() in ('true', '1', 'yes')

EMAIL_CONFIG = {
    'smtp_host': os.environ.get('SMTP_HOST', 'smtp.gmail.com'),
    'smtp_port': int(os.environ.get('SMTP_PORT', '587')),
    'smtp_user': os.environ.get('SMTP_USER', ''),
    'smtp_password': os.environ.get('SMTP_PASSWORD', ''),
    'from_email': os.environ.get('EMAIL_FROM', os.environ.get('SMTP_USER', '')),
    'resend_api_key': os.environ.get('RESEND_API_KEY', ''),
    'recipients': [
        r.strip()
        for r in os.environ.get('ALERT_RECIPIENTS', '').split(',')
        if r.strip()
    ],
}

MODEL_PATH = BASE_DIR / 'model' / 'failure_model.pkl'
