from .base import *
import dj_database_url

DEBUG = False
TEMPLATE_DEBUG = DEBUG

DATABASES['default'] = dj_database_url.config()

# Honor the 'X-Forwarded-Proto' header for request.is_secure()
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

ALLOWED_HOSTS = ['.thisisnotthatgame.com','.herokuapp.com', 'localhost', '127.0.0.1']

STATIC_URL = 'http://philipjohnjames.com/applesanon/static/'

TEMPLATE_DIRS = (
    PROJECT_ROOT.child('templates'),
)

USE_PUSHER = True
PUSHER_APP_ID = get_env_variable("PUSHER_APP_ID")
PUSHER_KEY = get_env_variable("PUSHER_KEY")
PUSHER_SECRET = get_env_variable("PUSHER_SECRET")

INSTALLED_APPS += (
    'gunicorn',
)

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
        'TIMEOUT': 3600,
    }
}
