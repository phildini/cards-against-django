from .base import *
import dj_database_url
import urlparse

DEBUG = False
TEMPLATE_DEBUG = DEBUG

DATABASES['default'] = dj_database_url.config()

REDIS_URL = urlparse.urlparse(get_env_variable('REDISCLOUD_URL'))

SOCKETIO_URL = get_env_variable("SOCKETIO_URL")

# Honor the 'X-Forwarded-Proto' header for request.is_secure()
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

ALLOWED_HOSTS = ['.thisisnotthatgame.com','.herokuapp.com', 'localhost', '127.0.0.1']

TINTG_SERVER = 'http://thisisnotthatgame.com'

STATIC_URL = 'http://philipjohnjames.com/applesanon/static/'

TEMPLATE_DIRS = (
    PROJECT_ROOT.child('templates'),
)

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
