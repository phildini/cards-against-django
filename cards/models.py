# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#

import datetime
import random
import hashlib
import urllib

from django.db import models
from django.db.models import F
from django.db.models.signals import pre_save
from django.contrib.auth.models import User

from jsonfield import JSONField
from model_utils.models import TimeStampedModel

# this is so wrong....
from django.utils.safestring import mark_safe
from django.utils.html import escape

import log


ONE_HOUR = datetime.timedelta(seconds=60*60*1)

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
        used_black_deck = [ of card black numbers ],
        used_white_deck = [ of card white numbers ],
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
        return mark_safe('%s %s - %s' % (is_active, modified_str, self.name))
    
    @classmethod
    def deactivate_old_games(cls, older_than=None):
        """`older_than` datetime to compare against, if not specified now - 2 hours is used.
        """
        older_than = older_than or (datetime.datetime.now() - (ONE_HOUR * 2))
        """NOTE for update below Django appears to have a bug with sqlite3,
        it generates bad SQL with the wrong string concat operator, e.g.:
        
            UPDATE "cards_game"
            SET
                "is_active" = 0,
                "name" = (('DONE ' + "cards_game"."modified") + ' - ') + "cards_game"."name" 
            WHERE ("cards_game"."is_active" = 1 AND "cards_game"."modified" <= '2013-04-18 23:32:48.338546' );
        
        wrong query uses "+" when it should use "||"
        
            UPDATE "cards_game"
            SET
                "is_active" = 0,
                "name" = (('DONE ' || "cards_game"."modified") || ' - ') || "cards_game"."name" 
            WHERE ("cards_game"."is_active" = 1 AND "cards_game"."modified" <= '2013-04-18 23:32:48.338546' );
        """
        cls.objects.filter(is_active=True, modified__lte=older_than).update(is_active=False, name='DONE ' + F('modified') + ' - ' + F('name'))

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
        self.check_have_needed_white_cards()
    
    def check_have_needed_white_cards(self):
        if self.gamedata['submissions']:
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
        else:
            if self.game_state == GAMESTATE_SELECTION:
                self.game_state = GAMESTATE_SUBMISSION
                self.gamedata['filled_in_texts'] = []
            
    
    def deal_white_card(self):
        if len(self.gamedata['white_deck']) == 0:
            # re-use discard white cards
            tmp_white_deck = self.gamedata['used_white_deck']
            self.gamedata['used_white_deck'] = []
            random.shuffle(tmp_white_deck)
            self.gamedata['white_deck'] = tmp_white_deck

        white_card = self.gamedata['white_deck'].pop()
        return white_card

    def start_new_round(self, czar_name=None, winner=None, winner_id=None):
        """NOTE this does not reset a game, it resets the cards on the table ready for the next round
        """
        white_submissions = self.gamedata['submissions']
        if self.gamedata['filled_in_texts'] and winner:
            for player_name, filled_in_text in self.gamedata['filled_in_texts']:
                if winner == player_name:
                    self.gamedata['prev_filled_in_question'] = filled_in_text
        self.gamedata['submissions'] = {}
        self.gamedata['card_czar'] = winner_id
        self.gamedata['round'] += 1
        self.gamedata['last_round_winner'] = winner
        self.gamedata['filled_in_texts'] = None
        self.game_state = GAMESTATE_SUBMISSION
        
        if winner:
            self.gamedata['players'][winner]['wins'] += 1

        # check the pick number of previous black card, deal that many cards
        prev_black_card_id = self.gamedata['current_black_card']
        if prev_black_card_id is not None:
            prev_black_card = BlackCard.objects.get(id=prev_black_card_id)
            pick = prev_black_card.pick

            # replace used white cards
            for _ in xrange(pick):
                for player_name in self.gamedata['players']:
                    # check we are not the card czar
                    if player_name != czar_name:
                        self.gamedata['players'][player_name]['hand'].append(self.deal_white_card())

        # deal new black card to game
        if len(self.gamedata['black_deck']) == 0:
            # re-use discard black cards
            tmp_black_deck = self.gamedata['used_black_deck']
            self.gamedata['used_black_deck'] = []
            random.shuffle(tmp_black_deck)
            self.gamedata['black_deck'] = tmp_black_deck
        self.gamedata['current_black_card'] = black_card = self.gamedata['black_deck'].pop()
        curr_black_card = BlackCard.objects.get(id=self.gamedata['current_black_card'])
        if prev_black_card_id is not None:
            self.gamedata['used_black_deck'].append(prev_black_card_id)

        # check if we draw additional cards based on black card
        # NOTE anyone who joins after this point will not be given the extra draw cards
        white_card_draw = curr_black_card.draw
        for _ in xrange(white_card_draw):
            for player_name in self.gamedata['players']:
                # check we are not the card czar
                if player_name != czar_name:
                    self.gamedata['players'][player_name]['hand'].append(self.deal_white_card())
        
        for tmp_name in white_submissions:
            for x in white_submissions[tmp_name]:
                self.gamedata['used_white_deck'].append(x)


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
            'round': 0,
            'card_czar': '',
            'white_deck': shuffled_white,
            'black_deck': shuffled_black,
            'used_white_deck': [],
            'used_black_deck': [],
            'mode': 'submitting',
            'filled_in_texts': None,
            'prev_filled_in_question': None,
        }

    # FIXME should be using a player object
    def create_player(self, player_name, player_image_url=None):
        """if player_image_url is ommited a default image is generated.
        """
        log.logger.debug("new player called")
        # Basic data obj for player. Eventually, this will be saved in cache.
        player_image_url = player_image_url or avatar_url(player_name)
        return {
            'hand': [],
            'wins': 0,
            'player_avatar': player_image_url,
        }

    def add_player(self, player_name, player_image_url=None):
        log.logger.debug(player_name)
        log.logger.debug(self.gamedata)
        if player_name not in self.gamedata['players']:
            player = self.create_player(player_name, player_image_url=player_image_url)
            player['hand'] = [
                self.deal_white_card() for x in xrange(10)
            ]
            self.gamedata['players'][player_name] = player
            # TODO if no czar make this player the card czar?
        # else do nothing, they are already in the game do NOT raise any errors

    def del_player(self, player_name):
        log.logger.debug(player_name)
        log.logger.debug(self.gamedata)
        if player_name in self.gamedata['players']:
            player = self.gamedata['players'][player_name]
            log.logger.debug('player %r', player)
            for tmp_card in player['hand']:
                self.gamedata['white_deck'].insert(0, tmp_card)
            # cardczar cleanup
            del self.gamedata['players'][player_name]
            if self.gamedata['card_czar'] == player_name:
                if self.gamedata['players']:
                    self.gamedata['card_czar'] = list(self.gamedata['players'].keys())[0]
                else:
                    self.gamedata['card_czar'] = ''
            
            # submissions cleanup
            if player_name in self.gamedata['submissions']:
                # remove and check if gamestate needs to change?
                for tmp_card in self.gamedata['submissions'][player_name]:
                    self.gamedata['white_deck'].insert(0, tmp_card)
                del self.gamedata['submissions'][player_name]
            self.check_have_needed_white_cards()
            
            # last_round_winner cleanup -- FIXME I'm not sure this is used/needed, remove from model/template? appears to only be used in old player template which should also be removed
            ### unset session name?? probably not a good idea

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
        log.logger.debug("black card, white_card_num_list %r", white_card_num_list)
        card_text = self.text
        num_blanks = card_text.count(BLANK_MARKER)
        assert self.pick == len(white_card_num_list)
        
        for tmp_num in range(num_blanks + 1, (self.pick - num_blanks) + 1):
            card_text = card_text + '</br> ' + BLANK_MARKER
        
        # assume num_blanks count is valid and len(white_card_num_list) == num_blanks
        white_card_text_dict = dict(WhiteCard.objects.filter(id__in=white_card_num_list).values_list('id', 'text'))
        log.logger.debug("black card, white_card_text_dict %r", white_card_text_dict)
        for white_id in white_card_num_list:
            white_text = white_card_text_dict[white_id]
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


class CardSet(models.Model):
    """
        class Card_Set(models.Model):  # Using underscore ensures "card_set_id" column name is used
    """
    active = models.BooleanField(default=True)
    name = models.CharField(max_length=255, unique=True)
    base_deck = models.BooleanField(default=True)
    description = models.CharField(max_length=255)
    weight = models.SmallIntegerField(default=0)
    black_card = models.ManyToManyField(BlackCard, db_table='card_set_black_card')
    white_card = models.ManyToManyField(WhiteCard, db_table='card_set_white_card')

    class Meta:
        db_table = 'card_set'
