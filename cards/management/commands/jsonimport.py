from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


# json support, TODO consider http://pypi.python.org/pypi/omnijson
try:
    # Python 2.6+
    import json
except ImportError:
    try:
        # from http://code.google.com/p/simplejson
        import simplejson as json
    except ImportError:
        json = None

if json is None:

    def dump_json(x, indent=None):
        """dumb not safe!
        Works for the purposes of this specific script as quotes never
        appear in data set.

        Parameter indent ignored"""
        if indent:
            result = pprint.pformat(x, indent)
        else:
            result = repr(x).replace("'", '"')
        return result

    def load_json(x):
        """dumb not safe! Works for the purposes of this specific script"""
        x = x.replace('\r', '')
        return eval(x)
else:
    dump_json = json.dumps
    load_json = json.loads

from cards.models import BlackCard, WhiteCard, CardSet


@transaction.commit_on_success
def dict2db(d, verbosity=1):
    for cardset_name in d:
        b_count = w_count = 0
        cs = d[cardset_name]
        description = cs.get('description')
        # TODO allow watermark to be shared for a cardset
        cardset = CardSet(name=cardset_name, description=description)
        if verbosity > 1:
            print cardset
            print cardset.description
        cardset.save()
        if verbosity > 1:
            print cardset
        blackcards = cs.get('blackcards')
        if blackcards:
            for entry in blackcards:
                if verbosity > 1:
                    print entry
                # TODO support tuples/lists as well as dict
                black_card = BlackCard(**entry)
                if verbosity > 1:
                    print repr(black_card)
                black_card.save()
                cardset.black_card.add(black_card)
                b_count += 1
        if verbosity > 1:
            print '-' * 65

        whitecards = cs.get('whitecards')
        if whitecards:
            for entry in whitecards:
                if verbosity > 1:
                    print entry
                white_card = WhiteCard(**entry)
                if verbosity > 1:
                    print repr(white_card)
                white_card.save()
                cardset.white_card.add(white_card)
                w_count += 1
        print cardset_name, b_count + w_count, '=', b_count, '+', w_count


class Command(BaseCommand):
    args = 'json_filename'
    help = 'Import card sets'

    def handle(self, *args, **options):
        filename = args[0]  # TODO error handling?
        self.stdout.write('Using %r' % filename)
        print ('%r' % filename)
        f = open(filename, 'rb')
        raw_str = f.read()
        f.close()

        d = load_json(raw_str)
        dict2db(d, int(options['verbosity']))
