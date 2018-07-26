import os
import sys
import environ

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Application directories
sys.path.append(os.path.join(BASE_DIR, "apps"))


env = environ.Env(
    DEBUG=(bool, False),
    DATABASE_URL=(str, ''),
    SECRET_KEY=(str, ''),
    ALLOWED_HOSTS=(list, []),
)

checkout_dir = environ.Path(__file__) - 2
assert os.path.exists(checkout_dir('manage.py'))

DEBUG = env.bool('DEBUG')

SECRET_KEY = env.str("SECRET_KEY")
if DEBUG and not SECRET_KEY:
    SECRET_KEY = 'xxx'

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')
if DEBUG:
    ALLOWED_HOSTS = ["*"]
DATABASES = {'default': env.db()}

# Application definition

INSTALLED_APPS = [
    # Django
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Own
    'core',
    'frontend',
    'repository',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ["templates"],
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

WSGI_APPLICATION = 'core.wsgi.application'

# Password validation
# https://docs.djangoproject.com/en/1.11/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "var/media/")

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "var/static/")
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
]
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.CachedStaticFilesStorage'


# Internationalization
# https://docs.djangoproject.com/en/1.11/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.11/howto/static-files/

STATIC_URL = '/static/'

# Custom settings

LOGIN_URL = '/login/'