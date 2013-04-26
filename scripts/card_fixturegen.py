#!/usr/bin/env python
# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#
"""This is not that game - data converter.

Converts (PostgresSQL) SQL files into Django fixture (json) data file.
"""

import os
import sys
import random
import pprint
import csv
import cgi
import sqlite3
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


DEFAULT_BLANK_MARKER = u"\uFFFD"  # u'_'
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
DJANGO_CARDS_DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'cards', 'fixtures')


class CardsParser(object):
    def __init__(self, blank=DEFAULT_BLANK_MARKER):
        self.blank = blank
        self.white_cards = []
        self.black_cards = []


def simple_select(c, sql_query, bind_params=None):
    """where c is a cursor"""
    print sql_query
    if bind_params is None:
        c.execute(sql_query)
    else:
        print bind_params
        c.execute(sql_query, bind_params)
    if c.description is not None:
        # We have a SELECT statement
        print c.description
        row = c.fetchone()
        while row:
            print row
            row = c.fetchone()
    print ''

def db2data(c, cp, django_data, json_style='django', fix_blank_count=True):
    # safe_fail=True, restrict_deck=None, 
    if json_style == 'django':
        black_cards_list = django_data
    else:
        black_cards_list = cp.black_cards
    c.execute('select text, pick, draw, id, watermark from black_cards order by id')
    for row in c:
        line = row[0]
        pick = row[1]
        draw = row[2]
        _id = row[3]
        watermark = row[4]
        num_blanks = line.count(cp.blank)
        if fix_blank_count:
            if num_blanks != pick and pick != 1:
                # temp workaround for picks > 1 when num blanks is 0
                tmp_text = []
                for tmp_num in range(num_blanks + 1, (pick - num_blanks) + 1):
                    tmp_text.append('%d: %s' % (tmp_num, cp.blank))
                line = line + ' ' + ' '.join(tmp_text)
                print 'FIXING', num_blanks, pick, pick - num_blanks, repr(line)
        if '_' in line.replace('<span class="card_number">', '<span class="cardnumber">'):
            print 'WARNING under found', repr(line)
            if safe_fail:
                raise NotImplementedError('found an underscore, this may not be a real problem')
        
        if json_style == 'django':
            entry = {
                'pk':_id,
                'model': 'cards.blackcard', 
                'fields': {'text': line, 'pick': pick, 'draw': draw, 'watermark': watermark,},
                }
        else:
            #entry = line
            #entry = (line, pick, draw)
            entry = {'text': line, 'pick': pick, 'draw': draw}
        black_cards_list.append(entry)
    cp.black_cards.sort()  # no need to sort alpha django black_cards_list.sort() the order should be correct already
    
    if json_style == 'django':
        white_cards_list = django_data
    else:
        white_cards_list = cp.white_cards

    c.execute('select text, id, watermark from white_cards order by id')
    for row in c:
        line = row[0]
        _id = row[1]
        watermark = row[2]

        # check for double underscore (may be a single underscore if there is html)
        if '_' in line.replace('<span class="card_number">', '<span class="cardnumber">'):
            print 'WARNING under found', repr(line)
            if safe_fail:
                raise NotImplementedError('found an underscore, this may not be a real problem')
        
        if json_style == 'django':
            entry = {
                'pk':_id,
                'model': 'cards.whitecard', 
                'fields': {'text': line, 'watermark': watermark,},
                }
        else:
            entry = line
        
        white_cards_list.append(entry)
    cp.white_cards.sort()
    

def sql2data(filename, safe_fail=True, restrict_deck=None, json_style='django', fix_blank_count=False):
    """Convert PostgresSQL files into json data file.
    
    If json_style == 'django', the json file is suitable for the model in
    use in https://github.com/phildini/cards-against-django/
    
    NOTE this routine will add blank markers if any are missing.
    
        281 black cards
        972 white cards
    """
    
    cp = CardsParser()
    django_data = []
    
    dbname = ':memory:'
    #dbname = 'cards.sqlite3'
    db = sqlite3.connect(dbname)
    c = db.cursor()
    
    all_ddl = """CREATE TABLE black_cards (
    id integer NOT NULL,
    text character varying(255) NOT NULL,
    draw smallint DEFAULT 0,
    pick smallint DEFAULT 1,
    watermark character varying(5)
);

    CREATE TABLE white_cards (
    id integer NOT NULL,
    text character varying(255) NOT NULL,
    watermark character varying(5)
);

CREATE TABLE card_set_black_card (
    card_set_id integer NOT NULL,
    black_card_id integer NOT NULL
);

CREATE TABLE card_set_white_card (
    card_set_id integer NOT NULL,
    white_card_id integer NOT NULL
);

CREATE TABLE card_set (
    id integer NOT NULL,
    active boolean NOT NULL,
    name character varying(255),
    base_deck boolean NOT NULL,
    description character varying(255)
);

"""
    
    for ddl in all_ddl.split(';'):
        c.execute(ddl)
    
    print 'reading %s' % filename
    f = open(filename, 'rb')
    for line in f:
        line_type = None
        if line.startswith('INSERT INTO black_cards VALUES ('):
            line = line.strip()
            line_type = 'BLACK'
        elif line.startswith('INSERT INTO white_cards VALUES ('):
            line = line.strip()
            line_type = 'WHITE'
        elif line.startswith('INSERT INTO card_set_black_card VALUES (') or line.startswith('INSERT INTO card_set_white_card VALUES ('):
            c.execute(line)
        elif line.startswith('INSERT INTO card_set VALUES ('):
            line = line.strip()
            line_type = 'cardset'
        if line_type:
            # quick-n-dirty true/false literal conversion, assumes they do not exist in string literals (card text)
            line = line.replace(', true', ', 1')
            line = line.replace(', false', ', 0')
            
            line = line.decode('utf8')
            # there appears to be variable length underscores in different rows
            line = line.replace('_____', cp.blank)
            line = line.replace('____', cp.blank)
            #print line_type, line
            c.execute(line)
    f.close()
    
    simple_select(c, 'select count(*) from black_cards')
    simple_select(c, 'select count(*) from white_cards')
    
    simple_select(c, 'select count(*) from card_set_black_card')
    simple_select(c, 'select count(*) from card_set_white_card')
    
    # remove cards not in a set (likely to be test cards)
    c.execute('delete from black_cards where id not in (select black_card_id from card_set_black_card)')
    c.execute('delete from white_cards where id not in (select white_card_id from card_set_white_card)')
    
    restrict_deck = True
    if restrict_deck:
        print '  ** Restricting card deck **'
        print ''
        # only use 2nd edition cards
        single_card_set_to_use = 'Second Version'
        c.execute('delete from black_cards where id not in (select black_card_id from card_set_black_card, card_set where card_set_id = id and name = ?)', (single_card_set_to_use,))
        c.execute('delete from white_cards where id not in (select white_card_id from card_set_white_card, card_set where card_set_id = id and name = ?)', (single_card_set_to_use,))
    
    simple_select(c, 'select count(*) from black_cards')
    simple_select(c, 'select count(*) from white_cards')

    db2data(c, cp, django_data, json_style=json_style, fix_blank_count=fix_blank_count)  # FIXME this is messy
    c.close()
    db.commit()
    db.close()
    
    if json_style == 'django':
        filename = os.path.join(DJANGO_CARDS_DATA_DIR, 'initial_data.json')
    else:
        filename = os.path.join(DATA_DIR, 'data.json')
    print 'writing %s' % filename
    if json_style == 'django':
        data = dump_json(django_data, indent=4)
        # now "fix" indentation to match Djago fixture formatting
        new_data = []
        for line in data.split('\n'):
            if line.startswith('    '):
                line = line[4:]
            if line.endswith('}, '):
                line = line[:-1]
            new_data.append(line)
        data = '\n'.join(new_data)
        f = open(filename, 'wb')
        f.write(data)
        f.write('\n')
        f.close()
    else:
        g = Game(cp.white_cards, cp.black_cards)
        print '%d black cards' % len(g.black_cards)
        print '%d white cards' % len(g.white_cards)
        g.save(filename)


def main(argv=None):
    if argv is None:
        argv = sys.argv
    
    # Dumb command line processing
    try:
        filename = argv[1]
    except IndexError:
        sql_filename = 'cah_cards.sql'  # https://raw.github.com/ajanata/PretendYoureXyzzy/master/cah_cards.sql
        filename = os.path.join(DATA_DIR, sql_filename)
    
    sql2data(filename)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
