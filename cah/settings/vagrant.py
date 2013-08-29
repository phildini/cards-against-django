from cah.settings.local import *

DATABASES = {
    'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': 'cah',
            'USER': 'cah',
            'PASSWORD': 'cah',
            'HOST': 'localhost',
            'PORT': '',
    }
}
