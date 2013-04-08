from .base import *

DEBUG = False
TEMPLATE_DEBUG = DEBUG

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

ALLOWED_HOSTS = ['*.herokuapp.com', 'localhost', '127.0.0.1']

STATIC_URL = 'http://philipjohnjames.com/applesanon/static/'

INSTALLED_APPS += (
    'gunicorn',
)