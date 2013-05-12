# Local settings
# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#

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
# MIDDLEWARE_CLASSES += \
#             ('debug_toolbar.middleware.DebugToolbarMiddleware', )

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
        'TIMOUT': 3600,
    }
}
STATIC_ROOT = ''
STATIC_URL = '/static/'
STATICFILES_DIRS = ()

USE_PUSHER = False

############
SITE_ROOT = '/tmp'  # FIXME loation for log file(s)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'standard': {
            #'format' : "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            'format' : '%(asctime)s %(filename)s:%(lineno)d %(funcName)s %(levelname)s %(message)s',
            'datefmt' : "%d/%b/%Y %H:%M:%S"
        },
    },
    'handlers': {
        'null': {
            'level':'DEBUG',
            'class':'django.utils.log.NullHandler',
        },
        'logfile': {
            'level':'DEBUG',
            'class':'logging.handlers.RotatingFileHandler',
            'filename': SITE_ROOT + "/logfile",
            'maxBytes': 50000,
            'backupCount': 2,
            'formatter': 'standard',
        },
        'console':{
            'level':'INFO',
            'class':'logging.StreamHandler',
            'formatter': 'standard'
        },
        'consoledebug':{
            'level':'DEBUG',
            'class':'logging.StreamHandler',
            'formatter': 'standard'
        },
    },
    'loggers': {
        'django': {
            'handlers':['console'],
            'propagate': True,
            'level':'WARN',
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'cah': {
            'handlers': ['consoledebug', 'logfile'],
            'level': 'DEBUG',
        },
    }
}
