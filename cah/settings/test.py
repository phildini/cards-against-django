from .base import *

DEBUG = True
TEMPLATE_DEBUG = DEBUG

SECRET_KEY = '1234567890'

DATABASES = {
        'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': 'cah_django.db',
                'USER': '',
                'PASSWORD': '',
                'HOST': 'localhost',
                'PORT': '',
        }
}

REDIS_HOST = 'http://example.com'
REDIS_PORT = '9000'
SOCKETIO_URL = 'http://example.com'