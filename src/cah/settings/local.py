# Local settings
from .base import *

DEBUG = True
TEAMPLATE_DEBUG = DEBUG

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

INSTALLED_APPS += ('debug_toolbar', )
INTERNAL_IPS = ('127.0.0.1',)
MIDDLEWARE_CLASSES += \
            ('debug_toolbar.middleware.DebugToolbarMiddleware', )