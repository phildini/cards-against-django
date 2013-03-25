#!/usr/bin/env python
# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#
"""Not Apples to Apples (tm) nor is it
Cards Against Humanity(tm).
"""

import os
import sys


def doit():
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    #data_dir = os.path.join(data_dir, '')
    white_cards_filename = os.path.join(data_dir, 'wcards.txt')
    print white_cards_filename
    f = open(white_cards_filename, 'rb')
    data = f.read()  # yup all of it at once
    f.close()
    
    # there are some non-ascii characters (e.g. TradeMark symbol)
    data = data.decode('utf-8')
    skip_start = 'cards='
    print repr(data)
    data = data[len(skip_start):]
    print repr(data)
    white_cards = data.split('<>')
    print repr(white_cards)
    white_cards_dict = zip(enumerate(white_cards))
    print repr(white_cards_dict )


def main(argv=None):
    if argv is None:
        argv = sys.argv
    
    doit()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
