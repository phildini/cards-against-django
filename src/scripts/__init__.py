#!/usr/bin/env python
# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#
"""Not Apples to Apples (tm) nor is it
Cards Against Humanity(tm).
"""

import os
import sys
import random
import pprint
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
#data_dir = os.path.join(data_dir, '')


class CardsParser(object):
    def __init__(self, blank=DEFAULT_BLANK_MARKER):
        self.blank = blank
        self.white_cards = []
        self.black_cards = []

    def parsefile(self, file_obj=None, look_for_blanks=False, existing_cards=None, sort_cards=True):
        """Read from already open file and chop up cards into a
        list of (Unicode) strings.
        This attempts to avoid duplicates and allows an existing list to be passed in,
        the returned list includes the existing_cards
        """
        skip_start = 'cards='
        blank_marker_in_file = '__________'
        card_seperator = '<>'
        existing_cards = existing_cards or []
        
        data = file_obj.read()  # yup all of it at once
        
        # there are some non-ascii characters (e.g. TradeMark symbol)
        data = data.decode('utf-8')
        data = data[len(skip_start):]
        
        if look_for_blanks:
            """Black cards ask questions which will have:
                * 0 blank markers
                * 1 blank markers
                * 2 blank markers
                * 3 blank markers - NOTE no *.txt files have this
            
            0 blank markers is a question, from a game play perspective
            this is the same as 1 blank marker.
            """
            data = data.replace(blank_marker_in_file, self.blank)
        
        card_list = data.split(card_seperator)
        
        # Remove duplicates
        result = existing_cards[:]  # copy the existing list but do not modify it
        for card in card_list:
            if card not in result:
                result.append(card)
        
        if sort_cards:
            result.sort()
        
        return result
    
    def loadfile(self, filename=None, black=False):
        filename = os.path.join(data_dir, filename)
        f = open(filename, 'rb')
        if black:
            self.black_cards = self.parsefile(f, look_for_blanks=True, existing_cards=self.black_cards)
        else:
            self.white_cards = self.parsefile(f, existing_cards=self.white_cards)
        f.close()



class Game(object):
    def __init__(self, white_cards=None, black_cards=None):
        self.setup(white_cards, black_cards)  # kinda bad form
        
    def setup(self, white_cards=None, black_cards=None):
        # Question cards
        self.white_cards = white_cards or []
        
        # Answer cards
        self.black_cards = black_cards or []
        
        self.blank = DEFAULT_BLANK_MARKER
        
        self.white_deck = range(len(self.white_cards))
        self.black_deck = range(len(self.black_cards))
        
        self.black_deck_used = []
        self.white_deck_used = []
    
    def shuffle(self):
        """Uses built in random, it may be better to plugin a better
        random init routine and/also consider using
        https://pypi.python.org/pypi/shuffle/
        
        Also take a look at http://code.google.com/p/gcge/
        """
        random.shuffle(self.white_deck)
        random.shuffle(self.black_deck)
    
    def sim_round(self):
        """Debug simulate a round/turn.
        """
        black_card = self.black_deck.pop()
        card = self.black_cards[black_card]
        num_blanks = card.count(self.blank)
        print card.replace(self.blank, '_____')
        # get some random answers
        if num_blanks == 0:
            to_get = 1
        elif num_blanks == 1:
            to_get = 1
        elif num_blanks == 2:
            to_get = 2
        elif num_blanks == 2:
            to_get = 3
        else:
            raise NotImplemented('%d count blanks' % num_blanks)
        answers = []
        for _ in range(to_get):
            answers.append(self.white_deck.pop())
        if num_blanks > 0:
            answer_str = card
            for card_num in answers:
                answer_str = answer_str.replace(self.blank, self.white_cards[card_num], 1)
            print answer_str
        else:
            for card_num in answers:
                print self.white_cards[card_num]
        
        # not sure we really need discard decks...
        self.black_deck_used.append(black_card)
        for card_num in answers:
            self.white_deck_used.append(card_num)
    
    def load(self, filename):
        model = {}
        f = open(filename, 'rb')
        data = f.read()
        f.close()
        model = load_json(data)
        self.setup(white_cards=model['white_cards'], black_cards=model['black_cards'])
        self.blank = model['blank']
    
    def save(self, filename):
        model = {}
        model['white_cards'] = self.white_cards
        model['black_cards'] = self.black_cards
        model['blank'] = self.blank
        data = dump_json(model, indent=4)
        f = open(filename, 'wb')
        f.write(data)
        f.write('\n')
        f.close()


def doit():
    """
    cp = CardsParser()
    
    print 'white_cards'
    filename = 'wcards.txt'
    print filename
    cp.loadfile(filename)

    print 'black cards'
    filename = 'bcards.txt'
    print filename
    cp.loadfile(filename, black=True)

    print 'black cards 1'
    filename = 'bcards1.txt'
    print filename
    cp.loadfile(filename, black=True)

    print 'black cards 2 - which all appear to be two blanks'
    filename = 'bcards2.txt'
    print filename
    cp.loadfile(filename, black=True)
    
    # NOTE: "__________ + __________ = __________?" should be added
    # NOTE Deal additional 3 is not documented
    
    for card in cp.black_cards:
        print card.count(cp.blank), repr(card)
    
    filename = os.path.join(data_dir, 'data.json')
    g = Game(cp.white_cards, cp.black_cards)
    g.save(filename)
    """
    filename = os.path.join(data_dir, 'data.json')
    g = Game()
    g.load(filename)
    g.shuffle()
    """
    for card in g.black_cards:
        print card.count(g.blank), repr(card)
    print g.white_deck
    print g.black_deck
    """
    g.sim_round()



def main(argv=None):
    if argv is None:
        argv = sys.argv
    
    doit()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
