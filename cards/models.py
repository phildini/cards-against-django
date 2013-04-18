# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#

import random
import hashlib
import urllib

from django.db import models
from django.db.models.signals import pre_save
from django.contrib.auth.models import User

from jsonfield import JSONField
from model_utils.models import TimeStampedModel

# this is so wrong....
from django.utils.safestring import mark_safe
from django.utils.html import escape

import log


def gravatar_url(email, size=50, default='monsterid'):
    """Generate url for Gravatar image
    email - email address
    default = default_image_url or default hash type, for more default
    options see http://en.gravatar.com/site/implement/images/
    """
    gravatar_url = "http://www.gravatar.com/avatar/" + hashlib.md5(email.lower()).hexdigest() + "?"
    if default:
        gravatar_url += urllib.urlencode({'d': default, 's': str(size)})
    else:
        gravatar_url += urllib.urlencode({'s': str(size)})
    return gravatar_url

avatar_url = gravatar_url


GAMESTATE_SUBMISSION = 'submission'
GAMESTATE_SELECTION = 'selection'
GAMESTATE_TRANSITION = 'transition'


class BaseGameException(Exception):
    pass


class GameError(BaseGameException):
    pass


class Game(TimeStampedModel):

    name = models.CharField(max_length=140, unique=True)  # could use pk, but we can use id.
    game_state = models.CharField(max_length=140)
    """game states;
        submission - waiting for white cards
        selection - waiting for czar
        transition - where new players get added into active list).
    """
    
    is_active = models.BooleanField(default=True)
    
    gamedata = JSONField()  # NOTE character export/import (and this includes Admin editing) screws up json payload....
    """gamedata  is a dict
    {
        players: {
            # index here is the same as for submissions,
            # also same as player_name in filled_in_texts tuples
            # also same as card_czar
            player1: {
                hand: [ of card numbers ],
                wins: int,
            },
            player2 {...},
            ...
        },
        current_black_card = None|int,
        submissions = {dict of player name: [list of card numbers]}
        round: int,  # round number where round 1 is the first round
        card_czar = NOTE this is currently a str of a player name # 'player1',  # int index into 'players'
        black_deck = [ of card black numbers ],
        white_deck = [ of card white numbers ],
        filled_in_texts = None | [ (player name, filled in black card text), .... ]
    }

    """

    def __unicode__(self):
        # FIXME add game start time?, include num players and rounds in display name
        # FIXME font tag is a html 4.0 and in html 5 css should be used
        # ....also this is so wrong....
        if self.is_active:
            is_active = '<font color="green">LIVE</font>'
        else:
            is_active = '<font color="red">DEAD</font>'
        modified_str = self.modified.strftime('%Y-%m-%d %H:%M')
        return mark_safe('%s %s - %s (%d players)' % (is_active, modified_str, self.name, len(self.gamedata['players'])))

    def submit_white_cards(self, player_id, white_card_list):
        """player_id is currently name, the index into submissions
        white_card_list - list of white card ids
        
        TODO sanity checks
            player has cards
        
        Currently this is called after form validation.
        """
        
        if self.gamedata['card_czar'] == player_id:
            raise GameError('Player "%s" is card czar and can\'t submit white cards' % player_id)
        if self.gamedata['submissions'].get(player_id):
            raise GameError('Player "%s" already submitted a card' % player_id)
        if player_id not in self.gamedata['players']:
            raise GameError('Player "%s" not in game "%s"' % (player_id, self.name))
        
        self.gamedata['submissions'][player_id] = white_card_list
        for card in white_card_list:
            self.gamedata['players'][player_id]['hand'].remove(card)
        
        if len(self.gamedata['submissions']) == len(self.gamedata['players']) - 1:
            # this was the last player to submit, now we are waiting on the card czar to pick a winner
            self.game_state = GAMESTATE_SELECTION
            
            # fill in black card blanks.... and cache in gamedata
            black_card_id = self.gamedata['current_black_card']
            temp_black_card = BlackCard.objects.get(id=black_card_id)
            filled_in_texts = []
            for player_name in self.gamedata['submissions']:
                white_card_list = self.gamedata['submissions'][player_name]
                tmp_text = temp_black_card.replace_blanks(white_card_list)
                filled_in_texts.append((player_name, tmp_text))
            random.shuffle(filled_in_texts)
            self.gamedata['filled_in_texts'] = filled_in_texts  # FIXME rename this
    
    def deal_black_card(self):
        black_card = self.gamedata['black_deck'].pop()
        """
        # FIXME card re-use. This mechanism won't work with cards in database
        # we need to keep track of used cards (especially if only a subset of cards are used)
        if len(self.gamedata['black_deck']) == 0:
            shuffled_black = range(len(black_cards))
            random.shuffle(shuffled_black)
            self.gamedata['black_deck'] = shuffled_black
        """
        return black_card
    
    def deal_white_card(self):
        white_card = self.gamedata['white_deck'].pop()
        return white_card

    def start_new_round(self, czar_name, winner=None, winner_id=None):
        """NOTE this does not reset a game, it resets the cards on the table ready for the next round
        """
        self.gamedata['submissions'] = {}

        black_card_id = self.gamedata['current_black_card']
        temp_black_card = BlackCard.objects.get(id=black_card_id)
        pick = temp_black_card.pick
        self.gamedata['current_black_card'] = self.deal_black_card()
        self.gamedata['players'][winner]['wins'] += 1
        self.gamedata['card_czar'] = winner_id
        self.gamedata['round'] += 1
        self.gamedata['last_round_winner'] = winner

        # replace used white cards
        for _ in xrange(pick):
            for player_name in self.gamedata['players']:
                # check we are not the card czar
                if player_name != czar_name:
                    self.gamedata['players'][player_name]['hand'].append(self.deal_white_card())

        # check if we draw additional cards based on black card
        # NOTE anyone who joins after this point will not be given the extra draw cards
        white_card_draw = temp_black_card.draw
        for _ in xrange(white_card_draw):
            for player_name in self.gamedata['players']:
                # check we are not the card czar
                if player_name != czar_name:
                    self.gamedata['players'][player_name]['hand'].append(self.deal_white_card())
                    
        self.gamedata['filled_in_texts'] = None
        
        self.game_state = GAMESTATE_SUBMISSION

    def create_game(self):
        log.logger.debug("New Game called")
        """Create shuffled decks
        uses built in random, it may be better to plug-in a better
        random init routine and/also consider using
        https://pypi.python.org/pypi/shuffle/

        Also take a look at http://code.google.com/p/gcge/
        """
        shuffled_white = [x[0] for x in WhiteCard.objects.values_list('id')]
        random.shuffle(shuffled_white)
        shuffled_black = [x[0] for x in BlackCard.objects.values_list('id')]
        random.shuffle(shuffled_black)

        self.game_state = GAMESTATE_SUBMISSION  # FIXME remove this and make calls to start_new_round()

        # Basic data object for a game. Eventually, this will be saved in cache.
        return {
            'players': {},
            'current_black_card': None,  # get a new one my shuffled_black.pop()
            'submissions': {},
            'round': 1,  # FIXME start_new_round() which is next round should be called at start of each round, when that is done this should be zero
            'card_czar': '',
            'white_deck': shuffled_white,
            'black_deck': shuffled_black,
            'mode': 'submitting',
            'filled_in_texts': None,
        }

    # FIXME should be using a player object
    def create_player(self, player_name):
        log.logger.debug("new player called")
        # Basic data obj for player. Eventually, this will be saved in cache.
        return {
            'hand': [],
            'wins': 0,
            'player_avatar': avatar_url(player_name),
        }

    def add_player(self, player_name):
        if player_name not in self.gamedata['players']:
            player = self.create_player(player_name)
            player['hand'] = [
                self.deal_white_card() for x in xrange(10)
            ]
            self.gamedata['players'][player_name] = player
        # else do nothing, they are already in the game do NOT raise any errors


def game_pre_save(sender, **kwargs):
    game = kwargs['instance']
    if not game.is_active:
        # and previously was active; kwargs['update_fields'] ....
        game.name = 'DONE %s - %s' % (game.modified, game.name)

pre_save.connect(game_pre_save, sender=Game)


class Player(TimeStampedModel):

    # These are the fields I can think of for now, but we're not using it yet,
    # so we can adjust as needed.
    name = models.CharField(max_length=140)
    game = models.ForeignKey(Game)
    user = models.ForeignKey(
        User,
        blank=True,
        null=True,
        on_delete=models.SET_NULL
    )
    player_data = JSONField(blank=True)
    wins = models.IntegerField(blank=True)

    def __str__(self):
        return self.name


BLANK_MARKER = u"\uFFFD"


class BlackCard(models.Model):
    text = models.CharField(max_length=255)
    draw = models.SmallIntegerField(default=0)
    pick = models.SmallIntegerField(default=1)
    watermark = models.CharField(max_length=5, null=True)

    class Meta:
        db_table = 'black_cards'

    def replace_blanks(self, white_card_num_list):
        card_text = self.text
        num_blanks = card_text.count(BLANK_MARKER)
        assert self.pick == len(white_card_num_list)
        
        for tmp_num in range(num_blanks + 1, (self.pick - num_blanks) + 1):
            card_text = card_text + '</br> ' + BLANK_MARKER
        
        # assume num_blanks count is valid and len(white_card_num_list) == num_blanks
        white_card_text_list = WhiteCard.objects.filter(id__in=white_card_num_list).values_list('text')
        for white_text, in white_card_text_list:
            white_text = white_text.rstrip('.')
            """We can't change the case of the first letter in case
            it is a real name :-( We'd need to consult a word list,
            to make that decision which is way too much effort at
            the moment."""
            white_text = '<strong>' + white_text + '</strong>'
            card_text = card_text.replace(BLANK_MARKER, white_text, 1)
        return card_text

    def __unicode__(self):
        return self.text


class WhiteCard(models.Model):
    text = models.CharField(max_length=255)
    watermark = models.CharField(max_length=5, null=True)

    class Meta:
        db_table = 'white_cards'

    def __unicode__(self):
        return self.text
