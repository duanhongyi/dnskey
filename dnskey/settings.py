"""
Django settings for dnskey project.

Generated by 'django-admin startproject' using Django 2.1.1.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.1/ref/settings/
"""

import os
from urllib.parse import urlparse

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '2xwp7g3cj^i=ro$_^ei=vn7bgn^yesux(wp(pf^$$a52dz3g4q'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = bool(int(os.environ.get('DNSKEY_DEBUG' , 1)))

ALLOWED_HOSTS = os.environ.get("DNSKEY_HTTP_ALLOWED_HOSTS", "*").split(",")


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

INSTALLED_APPS += [
    'dnskey',
    'domain',
    'monitor',
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

ROOT_URLCONF = 'dnskey.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'dnskey.wsgi.application'


# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases
# database url eg: postgresql://{username}:{password}@{host}:{port}/{database}
DATABASES = {}
DNSKEY_DATABASE_PRIMARY_LIST = os.environ.get("DNSKEY_DATABASE_PRIMARY_LIST")
DNSKEY_DATABASE_REPLICA_LIST = os.environ.get("DNSKEY_DATABASE_REPLICA_LIST")

def parse_database_list(prefix, database_list_url):
    for index, url in enumerate(database_list_url.split(",")):
        parse_result = urlparse(url)
        result = list(map(lambda x: x.split(":"), parse_result.netloc.split("@")))
        DATABASES['%s%s' % (prefix, index)] = {
            'ENGINE': 'django.db.backends.%s' % parse_result.scheme,
            'NAME': parse_result.path.replace('/', ''),
            'USER': result[0][0],
            'PASSWORD': result[0][1],
            'HOST': result[1][0],
            'PORT': int(result[1][1]),                   
        }
parse_database_list("primary.", DNSKEY_DATABASE_PRIMARY_LIST)
DATABASES['default'] = DATABASES[list(DATABASES.keys())[0]]

parse_database_list("replica.", DNSKEY_DATABASE_REPLICA_LIST)
DATABASE_ROUTERS = ['dnskey.routers.PrimaryReplicaRouter', ]

# Password validation
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/2.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/

STATIC_URL = '/static/'

CACHES = {
    'default': {
        'BACKEND': 'djmemcache.backend.PyMemcacheCache',
        'LOCATION': os.environ.get("DNSKEY_MEMCACACHE_SERVERS"),
        'OPTIONS': {
            'TIMEOUT': 600,
            'CONNECT_TIMEOUT': 30,
            'USE_POOLING': True,
        }
    }
}

DNSKEY_MAXIMUM_QUERY_DEPTH = int(os.environ.get(
    "DNSKEY_MAXIMUM_QUERY_DEPTH",
    "20"
))

DNSKEY_DATABASE_WHITELIST_TIMEOUT = int(os.environ.get(
    "DNSKEY_DATABASE_WHITELIST_TIMEOUT",
    "9"
))

DNSKEY_REMOTE_NAMESERVERS = os.environ.get(
    "DNSKEY_NAMESERVERS",
    "119.29.29.29:53,223.5.5.5:53,180.76.76.76:53"
).split(",")

DNSKEY_REMOTE_QUERY_TIMEOUT = int(os.environ.get("DNSKEY_REMOTE_QUERY_TIMEOUT", "3"))
DNSKEY_REMOTE_QUERY_PROTOCOL = os.environ.get("DNSKEY_REMOTE_QUERY_PROTOCOL", "UDP")

DNSKEY_DNS_SERVE_HOST = os.environ.get(
    "DNSKEY_DNS_SERVE_HOST",
    "::"
)

DNSKEY_DNS_SERVE_PORT = int(os.environ.get(
    "DNSKEY_DNS_SERVE_POST",
    "53"
))

DNSKEY_SERVER_WORKER_PROCESSES = int(os.environ.get(
    "DNSKEY_SERVER_WORKER_PROCESSES",
    "0"
))

DNSKEY_RECORD_RECENT_QUERY_TIMES_TIMEOUT  = int(os.environ.get(
    "DNSKEY_RECORD_RECENT_QUERY_TIMES_TIMEOUT",
    "900"
))

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_USE_TLS = bool(int(os.environ.get('DNSKEY_EMAIL_USE_TLS', 0)))
EMAIL_USE_SSL = bool(int(os.environ.get('DNSKEY_EMAIL_USE_SSL', 0)))
EMAIL_HOST = os.environ.get('DNSKEY_EMAIL_HOST')
EMAIL_PORT = int(os.environ.get('DNSKEY_EMAIL_PORT', 25))
EMAIL_TIMEOUT = int(os.environ.get('DNSKEY_EMAIL_TIMEOUT', 9))
EMAIL_HOST_USER = os.environ.get('DNSKEY_EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('DNSKEY_EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = os.environ.get('DNSKEY_DEFAULT_FROM_EMAIL')
EMAIL_SUBJECT_PREFIX = os.environ.get('DNSKEY_EMAIL_SUBJECT_PREFIX')
EMAIL_INTERVAL = int(os.environ.get('DNSKEY_EMAIL_INTERVAL', 300))
