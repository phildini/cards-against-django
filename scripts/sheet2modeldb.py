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
from django.db import connection
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
    
    
    """this is a terrible way to delete stuff....
    Game.objects.all().delete()
    BlackCard.objects.all().delete()
    WhiteCard.objects.all().delete()
    CardSet.objects.all().delete()
    # So instead use raw SQL
    """
    dmc = connection.cursor()  # Django Model Database Cursor
    for tablename in ['card_set_white_card', 'cards_game', 'cards_player', 'black_cards', 'card_set', 'card_set_black_card', 'white_cards']:
        dmc.execute('DELETE FROM %s' % tablename)
    dmc.close()
    
    cardset_dict = {}
    for card_ver in 'v1.0', 'v1.2', 'v1.3', 'v1.4':
        cardset = CardSet(name=card_ver, description=card_ver)
        cardset.save()
        cardset_dict[card_ver] = cardset
    
    #c.execute(""" select b."Text" as text, b."Special" as special, b."v1" as v10, b."v1.2" as v12, b."v1.3" as v13, b."v1.4" as v14 from "Main Deck Black" b order by text LIMIT 3""")
    c.execute(""" select b."Text" as text, b."Special" as special, b."v1" as v10, b."v1.2" as v12, b."v1.3" as v13, b."v1.4" as v14 from "Main Deck Black" b order by text """)
    print c.description
    for row_id, row in enumerate(c.fetchall(), 1):
        draw = 0

        print row_id, row
        card_text = row[0]
        special = row[1]
        v10 = row[2]
        v12 = row[3]
        v13 = row[4]
        v14 = row[5]
        if v10:
            # sync with other naming conventions
            v10 = 'v1.0'
        print (card_text, special, v10, v12, v13, v14)
        
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
        
        watermark = v10 or v12 or v13 or v14  # pick the first version it showed up in (or we could leave blank)
        black_card = BlackCard(text=card_text, draw=draw, pick=pick, watermark=watermark)
        print black_card
        black_card.save()
        tmp_dict = {'v1.0':v10, 'v1.2':v12, 'v1.3':v13, 'v1.4':v14}
        for card_ver in tmp_dict:
            #print card_ver, tmp_dict[card_ver]
            if tmp_dict[card_ver]:
                cardset = cardset_dict[card_ver]
                cardset.black_card.add(black_card)

    #c.execute(""" select w."Text" as text, w."v1.0" as v10, w."v1.2" as v12, w."v1.3" as v13, w."v1.4" as v14 from "Main Deck White" w order by text LIMIT 5""")
    c.execute(""" select w."Text" as text, w."v1.0" as v10, w."v1.2" as v12, w."v1.3" as v13, w."v1.4" as v14 from "Main Deck White" w order by text""")
    print c.description
    for row_id, row in enumerate(c.fetchall(), 1):
        print row_id, row
        card_text = row[0]
        v10 = row[1]
        v12 = row[2]
        v13 = row[3]
        v14 = row[4]
        
        watermark = v10 or v12 or v13 or v14  # pick the first version it showed up in (or we could leave blank)
        white_card = WhiteCard(text=card_text, watermark=watermark)
        print white_card
        white_card.save()
        tmp_dict = {'v1.0':v10, 'v1.2':v12, 'v1.3':v13, 'v1.4':v14}
        for card_ver in tmp_dict:
            #print card_ver, tmp_dict[card_ver]
            if tmp_dict[card_ver]:
                cardset = cardset_dict[card_ver]
                cardset.white_card.add(white_card)
    
    # this is probably not needed due to manual commit later
    for tmp_cardset_name in cardset_dict:
        cardset = cardset_dict[tmp_cardset_name]
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
