import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env.edge file if it exists
env_file = BASE_DIR / '.env.edge'
if env_file.exists():
    load_dotenv(env_file)
    print(f"[SETTINGS] Loaded environment from {env_file}")
else:
    print(f"[SETTINGS] No .env.edge file found, using environment variables")

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-change-this-in-production')
DEBUG = os.environ.get('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    
    # Third party
    'rest_framework',
    'rest_framework_simplejwt',
    'django_htmx',
    'widget_tweaks',
    'channels',
    'django_celery_beat',
    
    # Local apps
    'apps.core',
    'apps.pos',
    'apps.tables',
    'apps.kitchen',
    'apps.qr_order',
    'apps.promotions',
    'apps.management',  # Management Interface (Dashboard & Terminals)
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.core.middleware_session.SessionSafeguardMiddleware',  # Session protection
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
    'apps.core.middleware.TerminalMiddleware',  # Terminal detection
]

ROOT_URLCONF = 'pos_fnb.urls'

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
                'apps.core.context_processors.terminal_config',
                'apps.core.context_processors.store_config',
            ],
        },
    },
]

WSGI_APPLICATION = 'pos_fnb.wsgi.application'
ASGI_APPLICATION = 'pos_fnb.asgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'pos_fnb'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'password'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

# For development with SQLite
if os.environ.get('USE_SQLITE', 'False') == 'True':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Cache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1'),
    }
}

# Fallback to local memory cache if Redis not available
if os.environ.get('USE_LOCMEM_CACHE', 'False') == 'True':
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }

# Channels
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0')],
        },
    },
}

# Fallback to in-memory channel layer
if os.environ.get('USE_INMEMORY_CHANNEL', 'False') == 'True':
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Auth
AUTH_USER_MODEL = 'core.User'
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'  # Smart redirect in urls.py

# Internationalization
LANGUAGE_CODE = 'id'
TIME_ZONE = 'Asia/Jakarta'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Session Settings
SESSION_ENGINE = 'django.contrib.sessions.backends.db'  # Use database backend for reliability
SESSION_COOKIE_AGE = 86400  # 24 hours
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = False  # False for development (HTTP)
SESSION_SAVE_EVERY_REQUEST = True  # Ensure session is saved on every request
SESSION_COOKIE_NAME = 'pos_sessionid'  # Custom name to avoid conflicts
SESSION_COOKIE_PATH = '/'  # Ensure cookie is valid for all paths

# CSRF Settings
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8001',
    'http://127.0.0.1:8001',
    'http://localhost:8002',
    'http://127.0.0.1:8002',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]
CSRF_COOKIE_HTTPONLY = False  # Allow JavaScript to read CSRF cookie
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SECURE = False  # False for development (HTTP)
CSRF_USE_SESSIONS = False  # Use cookie-based CSRF (needed for forms)
CSRF_COOKIE_NAME = 'csrftoken'  # Explicit cookie name
CSRF_HEADER_NAME = 'HTTP_X_CSRFTOKEN'  # For AJAX requests

# Custom settings
BASE_URL = os.environ.get('BASE_URL', 'http://localhost:8000')

# Number formatting
USE_THOUSAND_SEPARATOR = True
THOUSAND_SEPARATOR = ','
NUMBER_GROUPING = 3

# Celery
CELERY_BROKER_URL = os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0')

# Print Agent Settings
PRINT_AGENT_AUTH_REQUIRED = os.environ.get('PRINT_AGENT_AUTH_REQUIRED', 'False') == 'True'
PRINT_AGENT_API_KEY = os.environ.get('PRINT_AGENT_API_KEY', 'your-secret-api-key-here')

# HO Server Sync Settings (for Edge Server)
HO_API_URL = os.environ.get('HO_API_URL', None)
HO_API_USERNAME = os.environ.get('HO_API_USERNAME', 'admin')
HO_API_PASSWORD = os.environ.get('HO_API_PASSWORD', 'admin123')

# Edge MinIO Settings (Object Storage for Product Images)
EDGE_MINIO_ENDPOINT = os.environ.get('EDGE_MINIO_ENDPOINT', 'localhost:9002')
EDGE_MINIO_ACCESS_KEY = os.environ.get('EDGE_MINIO_ACCESS_KEY', 'foodlife_admin')
EDGE_MINIO_SECRET_KEY = os.environ.get('EDGE_MINIO_SECRET_KEY', 'foodlife_secret_2026')
EDGE_MINIO_SECURE = os.environ.get('EDGE_MINIO_SECURE', 'False') == 'True'

# HO MinIO Settings (to download product images from HO)
HO_MINIO_ENDPOINT = os.environ.get('HO_MINIO_ENDPOINT', 'host.docker.internal:9000')
HO_MINIO_SECURE = os.environ.get('HO_MINIO_SECURE', 'False') == 'True'

# REST Framework & JWT Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
}

from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=24),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': False,
    'UPDATE_LAST_LOGIN': False,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
}

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}
