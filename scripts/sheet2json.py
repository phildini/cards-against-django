#!/usr/bin/env python
# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#
"""Convert a spreadsheet CAH from

    http://boardgamegeek.com/thread/947849/hopefully-more-than-complete-listing-of-all-offici

    https://docs.google.com/spreadsheet/ccc?key=0Ajv9fdKngBJ_dHFvZjBzZDBjTE16T3JwNC0tRlp6Wnc#gid=10
    
    https://docs.google.com/spreadsheet/ccc?key=0Ajv9fdKngBJ_dHFvZjBzZDBjTE16T3JwNC0tRlp6Wnc&output=xls
    
        mkdir data
        cd data
        wget 'https://docs.google.com/spreadsheet/ccc?key=0Ajv9fdKngBJ_dHFvZjBzZDBjTE16T3JwNC0tRlp6Wnc&output=xls' '--output-document=Cards Against Humanity versions.xlsx'

into db
"""

import os
import sys
import sqlite3
import urllib2

import xls2db  # from https://github.com/clach04/xls2db/
import xlrd

from card_fixturegen import DJANGO_CARDS_DATA_DIR

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

data_dir = os.path.join(os.path.dirname(__file__), 'data')


class MyHTTPRedirectHandler(urllib2.HTTPRedirectHandler):
    def http_error_302(self, req, fp, code, msg, headers):
        print "302 redirecting...."
        return urllib2.HTTPRedirectHandler.http_error_302(self, req, fp, code, msg, headers)

    http_error_301 = http_error_303 = http_error_307 = http_error_302

def wget(url):
    print 'opening %s' % url
    cookieprocessor = urllib2.HTTPCookieProcessor()
    opener = urllib2.build_opener(MyHTTPRedirectHandler, cookieprocessor)
    urllib2.install_opener(opener)
    response = urllib2.urlopen(url)
    result = response.read()
    response.close()
    return result


def x2db():
    
    db.commit()
    db.close()

def doit():
    column_name_start_row = 2  # NOTE 0 is the first line (so row number in sheet - 1)
    data_start_row = 4  # NOTE 0 is the first line (so row number in sheet - 1)
    dbname = ':memory:'
    #dbname = os.path.join(data_dir, 'tmpdb.db')
    
    db = sqlite3.connect(dbname)
    
    do_drop = True

    xfdata = wget('https://docs.google.com/spreadsheet/ccc?key=0Ajv9fdKngBJ_dHFvZjBzZDBjTE16T3JwNC0tRlp6Wnc&output=xls')
    xf = xlrd.open_workbook(file_contents=xfdata)
    xls2db.xls2db(xf, db, column_name_start_row=column_name_start_row, data_start_row=data_start_row, do_drop=do_drop)

    c = db.cursor()
    
    all_cards = []
    dumb_restrict = """ where "v1.4" is not NULL and "v1.4" <> '' """
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
        """
        if '+' in card_text:
            import pdb ; pdb.set_trace()
        """
        
        if special:
            print row
            if special == 'PICK 2':
                pick = 2
            elif special == 'DRAW 2, PICK 3':
                draw = 2
                pick = 3
            else:
                raise NotImplementedError('unrecognized special')
        
        black_card = {"pk": row_id, "model": "cards.blackcard", "fields": {"text":card_text, "draw": draw, "watermark": "v1.4", "pick": pick}}
        all_cards.append(black_card)
    
    c.execute(""" select "Text" as text from "Main Deck White" """ + dumb_restrict + 'order by text')
    print c.description
    for row_id, row in enumerate(c.fetchall(), 1):
        print row_id, row
        card_text = row[0]
        white_card = {"pk": row_id, "model": "cards.whitecard", "fields": {"text":card_text, "watermark": "v1.4"}}
        all_cards.append(white_card)
    
    db.commit()
    db.close()
    
    filename = os.path.join(DJANGO_CARDS_DATA_DIR, 'initial_data.json')
    print 'writing %s' % filename
    data = dump_json(all_cards, indent=4)
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



def main(argv=None):
    if argv is None:
        argv = sys.argv
    
    doit()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
