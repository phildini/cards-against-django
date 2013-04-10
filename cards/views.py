# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#

# Vision for data structure to be stored in cache:

# games: {
#     game1: {
#         players: {
#             player1: {
#                 hand: [...],
#                 wins: int,
#                 submitted = current submitted card,
#             },
#             player2 {...},
#             ...
#         },
#         current_black_card = None|int,
#         submissions = [dict of player submissions for the round],
#         round: int,
#         card_czar = 'player1',  # int index into 'players'
#         black_deck = [],
#         white_deck = [],
#     },
#     game2 {...},
#     ...
# }

# Contract between LobbyView and PlayerView:
#
# LobbyView will give PlayerView a named player and a game stored in cache.
# PlayerView will return to LobbyView any request that does not have those things.
# On the cache, 'players' will hav a mapping of ids to players.

import os
import json
import random
import hashlib
import urllib

from django.conf import settings
from django.utils.safestring import mark_safe
from django.views.generic import FormView
from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.core.cache import cache
from forms import PlayerForm, GameForm, CzarForm
import log
import uuid

from models import BlackCard, WhiteCard, Game


BLANK_MARKER = u"\uFFFD"


def gravatar_robohash_url(email, size=50):
    """Generate url for RoboHash image  (gravatar first then robohash)"""
    text_to_hash = hashlib.md5(email.lower()).hexdigest()
    robohash_url = "http://robohash.org/%s?size=%dx%d&gravatar=hashed" % (text_to_hash, size, size)
    return robohash_url

def gravatar_url(email, size=50, default='monsterid'):
    """Generate url for Gravatar image
    email - email address
    default = default_image_url or default hash type
    """
    gravatar_url = "http://www.gravatar.com/avatar/" + hashlib.md5(email.lower()).hexdigest() + "?"
    if default:
        gravatar_url += urllib.urlencode({'d': default, 's': str(size)})
    else:
        gravatar_url += urllib.urlencode({'s': str(size)})
    return gravatar_url

avatar_url = gravatar_robohash_url
avatar_url = gravatar_url


class PlayerView(FormView):

    template_name = 'player.html'
    form_class = PlayerForm

    def __init__(self, *args, **kwargs):
        super(PlayerView, self).__init__(*args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        # Setup for game and player

        self.player_id = self.request.session.get('player_id')

        session_ids = cache.get('session_ids', {})
        session_details = session_ids.get(self.player_id, {})
        if not session_details:
            return redirect(reverse('lobby-view'))

        self.game_name = session_details['game']
        self.player_name = session_details['name']

        try:
            self.game_dbobj = Game.objects.get(name=self.game_name)  # FIXME his name is horrible
            self.game_data = self.game_dbobj.gamedata
        except Game.DoesNotExist:
            return redirect(reverse('lobby-view'))
        if not self.game_data:
            return redirect(reverse('lobby-view'))
        self.is_card_czar = self.game_data['card_czar'] == self.player_id
        log.logger.debug('id %r name %r game %r', self.player_id, self.player_name, self.game_name)
        log.logger.debug('self.game_data %r', self.game_data)

        self.player_data = self.game_data['players'].get(self.player_name)
        # Deal hand if player doesn't have one.
        if not self.player_data['hand']:
            self.player_data['hand'] = [
                self.game_data['white_deck'].pop() for x in xrange(10)
            ]

        # Deal black card if game doesn't have one.
        if self.game_data['current_black_card'] is None:
            # FIXME call reset, do not manually deal black card here; what if the black card is a "draw 3, pick 2" card.
            self.game_data['current_black_card'] = self.deal_black_card()
        self.write_state()

        if self.is_card_czar:
            self.form_class = CzarForm
        return super(PlayerView, self).dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('player-view')

    def get_context_data(self, *args, **kwargs):
        context = super(PlayerView, self).get_context_data(*args, **kwargs)
        context['players'] = self.game_data['players']
        last_round_winner = self.game_data.get('last_round_winner', '')
        context['last_round_winner'] = last_round_winner
        if last_round_winner:
            context['last_round_winner_avatar'] = self.game_data['players'][last_round_winner]['player_avatar']
        context['black_card'] = self.black_card.replace(BLANK_MARKER, '______')
        context['player_name'] = self.player_name
        context['player_avatar'] = self.game_data['players'][self.player_name]['player_avatar']
        context['game_name'] = self.game_name
        context['show_form'] = self.can_show_form()
        # Display filled-in answer if player has submitted.
        if self.game_data['submissions'] and not self.is_card_czar:
            player_submission = self.game_data['submissions'].get(self.player_id)
            context['filled_in_question'] = self.replace_blanks(player_submission)
        context['action'] = reverse('player-view')
        return context

    def get_form_kwargs(self):
        black_card_id = self.game_data['current_black_card']
        temp_black_card = BlackCard.objects.get(id=black_card_id)
        black_card_text = temp_black_card.text
        self.black_card = black_card_text
        kwargs = super(PlayerView, self).get_form_kwargs()
        if self.is_card_czar:
            kwargs['cards'] = [
                (player_id, mark_safe(self.replace_blanks(self.game_data['submissions'][player_id]))) for player_id in self.game_data['submissions']
            ]
        else:
            kwargs['blanks'] = temp_black_card.pick
            # FIXME many singleton selects here, also only need one column
            kwargs['cards'] = tuple(
            
                (card, mark_safe(WhiteCard.objects.get(id=card).text)) for card in self.player_data['hand']
            )
        return kwargs

    def form_valid(self, form):
        if self.is_card_czar:
            session_ids = cache.get('session_ids')
            winner = form.cleaned_data['card_selection']
            log.logger.debug(winner)
            winner_name = session_ids[winner].get('name')
            self.reset(winner_name, winner)

        else:
            submitted = form.cleaned_data['card_selection']
            # The form returns unicode strings. We want ints in our list.
            self.game_data['submissions'][self.player_id] = [int(card) for card in submitted]
            for card in self.game_data['submissions'][self.player_id]:
                self.player_data['hand'].remove(card)
            log.logger.debug('%r', form.cleaned_data['card_selection'])
        self.write_state()
        return super(PlayerView, self).form_valid(form)

    def write_state(self):
        self.game_data['players'][self.player_name] = self.player_data
        self.game_dbobj.save()

    def can_show_form(self):
        flag = False
        # import pdb; pdb.set_trace()
        if self.game_data['card_czar'] == self.player_id:
            if not self.game_data['submissions']:
                flag = False
            elif len(self.game_data['submissions']) == len(self.game_data['players']) - 1:
                flag = True
            else:
                flag = False
        else:
            if self.player_id in self.game_data['submissions']:
                flag = False
            else:
                flag = True
        return flag

    def replace_blanks(self, white_card_num_list):
        card_text = self.black_card
        num_blanks = card_text.count(BLANK_MARKER)
        # assume num_blanks count is valid and len(white_card_num_list) == num_blanks
        if num_blanks == 0:
            card_num = white_card_num_list[0]
            white_text = WhiteCard.objects.get(id=card_num).text
            white_text = '<strong>' + white_text + '</strong>'
            card_text = card_text + ' ' + white_text
        else:
            for card_num in white_card_num_list:
                white_text = WhiteCard.objects.get(id=card_num).text
                white_text = white_text.rstrip('.')
                """We can't change the case of the first letter in case
                it is a real name :-( We'd need to consult a word list,
                to make that decision which is way too much effort at
                the moment."""
                white_text = '<strong>' + white_text + '</strong>'
                card_text = card_text.replace(BLANK_MARKER, white_text, 1)
        return card_text

    def reset(self, winner=None, winner_id=None):
        """NOTE this does not reset a game, it resets the cards on the table ready for the next round
        """
        self.game_data['submissions'] = {}
        
        black_card_id = self.game_data['current_black_card']
        temp_black_card = BlackCard.objects.get(id=black_card_id)
        pick = temp_black_card.pick
        self.game_data['current_black_card'] = self.deal_black_card()
        self.game_data['players'][winner]['wins'] += 1
        self.game_data['card_czar'] = winner_id
        self.game_data['round'] += 1
        self.game_data['last_round_winner'] = winner

        # replace used white cards
        for _ in xrange(pick):
            for player_name in self.game_data['players']:
                # check we are not the card czar
                if player_name != self.player_name:
                    self.game_data['players'][player_name]['hand'].append(self.game_data['white_deck'].pop())

        # check if we draw additional cards based on black card
        # NOTE anyone who joins after this point will not be given the extra draw cards
        white_card_draw = temp_black_card.draw
        for _ in xrange(white_card_draw):
            for player_name in self.game_data['players']:
                # check we are not the card czar
                if player_name != self.player_name:
                    self.game_data['players'][player_name]['hand'].append(self.game_data['white_deck'].pop())

    def deal_black_card(self):
        black_card = self.game_data['black_deck'].pop()
        """
        # FIXME card re-use. This mechanism won't work with cards in database
        # we need to keep track of used cards (especially if only a subset of cards are used)
        if len(self.game_data['black_deck']) == 0:
            shuffled_black = range(len(black_cards))
            random.shuffle(shuffled_black)
            self.game_data['black_deck'] = shuffled_black
        """
        return black_card


class LobbyView(FormView):

    template_name = 'lobby.html'
    form_class = GameForm

    def __init__(self, *args, **kwargs):
        self.game_list = [(game.name, game.name) for game in Game.objects.all()]  # FIXME this is terrible
        self.player_counter = cache.get('player_counter', 0)  # this doesn't really count players, it counts number of lobby views

    # def dispatch(self, request, *args, **kwargs):
        # return super(PlayerView, self).dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('player-view')

    def get_context_data(self, *args, **kwargs):
        context = super(LobbyView, self).get_context_data(*args, **kwargs)
        context['show_form'] = True
        self.player_id = self.request.session.get('player_id')
        if isinstance(self.player_id, uuid.UUID):
            # temp hack, to use strings for uuid incase cookie still around from old version
            self.player_id = str(self.player_id)
            self.request.session['player_id'] = self.player_id
        if not self.player_id:
            self.player_id = str(uuid.uuid1())
            self.request.session['player_id'] = self.player_id
        self.player_counter = cache.get('player_counter', 0) + 1
        cache.set('player_counter', self.player_counter)
        context['player_counter'] = self.player_counter
        log.logger.debug('self.player_id uuid %r', self.player_id)

        return context

    def get_form_kwargs(self):
        kwargs = super(LobbyView, self).get_form_kwargs()
        if self.game_list:
            kwargs['game_list'] = self.game_list
        kwargs['player_counter'] = self.player_counter
        return kwargs

    def form_valid(self, form):
        self.player_id = self.request.session.get('player_id')
        player_name = form.cleaned_data['player_name']

        existing_game = True
        # Set the game properties in the cache
        game_name = form.cleaned_data['new_game']
        if game_name:
            # Attempting to create a new game
            try:
                # see if already exists
                existing_game = Game.objects.get(name=game_name)
            except Game.DoesNotExist:
                existing_game = None
            if not existing_game:
                # really a new game
                new_game = self.create_game()
                new_game['players'][player_name] = self.create_player(player_name)
                new_game['card_czar'] = self.player_id
                tmp_game = Game(name=form.cleaned_data['new_game'])
                tmp_game.gamedata = new_game
                tmp_game.save()
        if existing_game:
            if not game_name:
                game_name = form.cleaned_data.get('game_list')
            existing_game = Game.objects.get(name=game_name)  # existing_game maybe a bool
            log.logger.debug('existing_game %r', (game_name, player_name,))
            log.logger.debug('existing_game.gamedata %r', (existing_game.gamedata,))
            log.logger.debug('existing_game.gamedata players %r', (existing_game.gamedata['players'],))
            if not existing_game.gamedata['players'].get(player_name):
                existing_game.gamedata['players'][player_name] = self.create_player(player_name)
            else:
                # FIXME
                raise NotImplementedError('joining with player names alreaady in same game causes problems')
            existing_game.save()

        # Set the player properties in the cache
        session_ids = cache.get('session_ids', {})
        session_details = session_ids.get(self.player_id, {})
        session_details['name'] = player_name
        session_details['game'] = game_name
        session_ids[self.player_id] = session_details
        cache.set('session_ids', session_ids)

        return super(LobbyView, self).form_valid(form)

    def create_game(self):
        log.logger.debug("New Game called")
        """Create shuffled decks
        uses built in random, it may be better to plug-in a better
        random init routine and/also consider using
        https://pypi.python.org/pypi/shuffle/

        Also take a look at http://code.google.com/p/gcge/
        """
        # FIXME only need id attributes
        shuffled_white = [w.id for w in WhiteCard.objects.all()]
        random.shuffle(shuffled_white)
        shuffled_black = [b.id for b in BlackCard.objects.all()]
        random.shuffle(shuffled_black)

        # Basic data object for a game. Eventually, this will be saved in cache.
        return {
            'players': {},
            'current_black_card': None,  # get a new one my shuffled_black.pop()
            'submissions': {},
            'round': 0,
            'card_czar': '',
            'white_deck': shuffled_white,
            'black_deck': shuffled_black,
            'mode': 'submitting',
        }

    def create_player(self, player_name):
        log.logger.debug("new player called")
        # Basic data obj for player. Eventually, this will be saved in cache.
        return {
            'hand': [],
            'wins': 0,
            'player_avatar': avatar_url(player_name),
        }
