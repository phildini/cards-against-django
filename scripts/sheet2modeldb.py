#!/usr/bin/env python
# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#
"""Convert a spreadsheet CAH from

    http://boardgamegeek.com/thread/947849/hopefully-more-than-complete-listing-of-all-offici

    https://docs.google.com/spreadsheet/ccc?key=0Ajv9fdKngBJ_dHFvZjBzZDBjTE16T3JwNC0tRlp6Wnc#gid=10
    
    https://docs.google.com/spreadsheet/ccc?key=0Ajv9fdKngBJ_dHFvZjBzZDBjTE16T3JwNC0tRlp6Wnc&output=xls
    
    into temp db and then from db into cards.model


    PYTHONPATH=`pwd` python scripts/sheet2modeldb.py

"""

import os
import sys
import sqlite3
import urllib2

"""
import xls2db  # from https://github.com/clach04/xls2db/
import xlrd
"""


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cah.settings.local")  # FIXME
from django.conf import settings
import django.db.transaction
import cards.models
from cards.models import BlackCard, WhiteCard, CardSet, Game
from card_fixturegen import DEFAULT_BLANK_MARKER, DATA_DIR


def doit():
    dbname = ':memory:'
    dbname = os.path.join(DATA_DIR, 'tmpdb.db')
    db = sqlite3.connect(dbname)
    c = db.cursor()

    # TODO read from spreadsheet into temp database "dbname"
    
    settings.DATABASES['default']['AUTOCOMMIT'] = False
    print dir(django.db.transaction)
    print dir(django.db.transaction.connections)
    django.db.transaction.commit_manually()
    #django.db.transaction.set_autocommit(False)
    
    
    Game.objects.all().delete()
    BlackCard.objects.all().delete()
    WhiteCard.objects.all().delete()
    CardSet.objects.all().delete()
    
    card_ver = 'v1.4'
    
    cardset = CardSet(name=card_ver, description=card_ver)
    cardset.save()
    
    dumb_restrict = """ where "%s" is not NULL and "%s" <> '' """ % (card_ver, card_ver)
    print dumb_restrict


    c.execute(""" select "Text" as text, "Special" as special from "Main Deck Black" """ + dumb_restrict + 'order by text')
    print c.description
    for row_id, row in enumerate(c.fetchall(), 1):
        draw = 0

        print row_id, row
        card_text = row[0]
        special = row[1]
        
        card_text = card_text.replace('______', DEFAULT_BLANK_MARKER)
        if '_' in card_text:
            raise NotImplementedError('found an underscore, this may not be a real problem')
        
        pick = card_text.count(DEFAULT_BLANK_MARKER)
        if pick < 1:
            pick = 1
        
        if special:
            print row
            if special == 'PICK 2':
                pick = 2
            elif special == 'DRAW 2, PICK 3':
                draw = 2
                pick = 3
            else:
                raise NotImplementedError('unrecognized special')
        
        black_card = BlackCard(text=card_text, draw=draw, pick=pick, watermark=card_ver)
        print black_card
        black_card.save()
        cardset.black_card.add(black_card)

    c.execute(""" select "Text" as text from "Main Deck White" """ + dumb_restrict + 'order by text')
    print c.description
    for row_id, row in enumerate(c.fetchall(), 1):
        print row_id, row
        card_text = row[0]
        white_card = WhiteCard(text=card_text, watermark=card_ver)
        print white_card
        white_card.save()
        cardset.white_card.add(white_card)
    cardset.save()

    django.db.transaction.commit()
    
    c.close()
    db.commit()
    db.close()




def main(argv=None):
    if argv is None:
        argv = sys.argv
    
    doit()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
