from optparse import make_option

# json support, TODO consider http://pypi.python.org/pypi/omnijson
try:
    # Python 2.6+
    import json
except ImportError:
    # from http://code.google.com/p/simplejson
    import simplejson as json

dump_json = json.dumps
load_json = json.loads

from django.core.management.base import BaseCommand, CommandError

from cards.models import dict2db


class Command(BaseCommand):
    args = 'json_filename'
    help = dict2db.__doc__
    option_list = BaseCommand.option_list + (
        make_option('--replace_existing',
            action='store_true',
            dest='replace_existing',
            default=False,
            help='Allow replacement (delete then add) of existing cardsets'),
        )

    def handle(self, *args, **options):
        filename = args[0]  # TODO error handling?
        verbosity = int(options['verbosity'])
        replace_existing = options['replace_existing']
        if verbosity >= 1:
            self.stdout.write('Using %r' % filename)
        f = open(filename, 'rb')
        raw_str = f.read()
        f.close()

        d = load_json(raw_str)
        results = dict2db(d, verbosity, replace_existing)
        for cardset_name, b_count, w_count in results:
            if verbosity >= 1:
                print '%s total# %d question# %d answer# %d' % (cardset_name, b_count + w_count, b_count, w_count)
