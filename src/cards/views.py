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
import cgi

from django.conf import settings
from django.views.generic import FormView, TemplateView
from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.core.cache import cache
from forms import PlayerForm, GameForm, CzarForm
from game import Game
from pprint import pprint
import log
import uuid


# Grab data from the cards json and set global, unaltered decks.
with open(os.path.join(settings.PROJECT_ROOT, 'data/data.json')) as data:
    cards = json.loads(data.read())
    black_cards = cards['black_cards']
    white_cards = cards['white_cards']
    blank_marker = cards['blank']


def gravatar_robohash_url(email, size=50):
    """Generate url for RoboHash image  (gravatar first then robohash)"""
    text_to_hash = hashlib.md5(email.lower()).hexdigest()
    robohash_url = "http://robohash.org/%s?size=%dx%d&gravatar=hashed" % (text_to_hash, size, size)
    return robohash_url


class PlayerView(FormView):

    template_name = 'player.html'
    form_class = PlayerForm

    def __init__(self, *args, **kwargs):
        super(PlayerView, self).__init__(*args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        # Setup for game and player
        # log.logger.debug('%r', self.request.session)
        if not self.request.session.get('game_name') or not self.request.session.get('player_name'):
            return redirect(reverse('lobby-view'))
        
        self.game_name = self.request.session.get('game_name')
        self.player_name = self.request.session.get('player_name')
        self.player_avatar = self.request.session.get('player_avatar')
        self.player_id = self.request.session.get('player_id')

        try:
            self.game_data = cache.get('games').get(self.game_name)
        except AttributeError:
            return redirect(reverse('lobby-view'))
        if not self.game_data:
            return redirect(reverse('lobby-view'))
        self.is_card_czar = self.game_data['card_czar'] == self.player_id

        # log.logger.debug(self.game_data)
        # log.logger.debug(self.player_name)
        self.player_data = self.game_data['players'].get(self.player_name)
        # Deal hand if player doesn't have one.
        # log.logger.debug('%r', self.player_data)
        if not self.player_data['hand']:
            self.player_data['hand'] = [
                self.game_data['white_deck'].pop() for x in xrange(10)
            ]

        # Deal black card if game doesn't have one.
        # FIXME: Game setup.
        if not self.game_data['current_black_card']:
            self.game_data['current_black_card'] = self.game_data['black_deck'].pop()
        pprint(self.game_data['players'])
        self.write_state()

        if self.is_card_czar:
            self.form_class = CzarForm
        return super(PlayerView, self).dispatch(request, *args, **kwargs)


    def get_success_url(self):
        return reverse('player-view')

    def get_context_data(self, *args, **kwargs):

        context = super(PlayerView, self).get_context_data(*args, **kwargs)
        context['last_round_winner'] = self.game_data.get('last_round_winner', '')
        num_blanks = self.black_card.count(blank_marker)
        context['black_card'] = self.black_card.replace(blank_marker, '______')
        context['player_name'] = self.player_name
        context['player_avatar'] = self.player_avatar
        context['game_name'] = self.game_name
        context['show_form'] = self.can_show_form()
        # Display filled-in answer if player has submitted.
        if self.game_data['submissions'] and not self.is_card_czar:
            player_submission = self.game_data['submissions'].get(self.player_id)
            context['filled_in_question'] = self.replace_blanks(player_submission, html=True)
        context['action'] = reverse('player-view')
        return context

    def get_form_kwargs(self):
        self.black_card = black_cards[self.game_data['current_black_card']]
        kwargs = super(PlayerView, self).get_form_kwargs()
        if self.is_card_czar:
            kwargs['cards'] = [(player_id, self.replace_blanks(self.game_data['submissions'][player_id])) for player_id in self.game_data['submissions']]
            log.logger.debug(kwargs['cards'])
        else:
            kwargs['blanks'] = black_cards[self.game_data['current_black_card']].count(blank_marker) or 1
            kwargs['cards'] = tuple(
                (card, white_cards[card]) for card in self.player_data['hand']
            )
        return kwargs

    def form_valid(self, form):
        if self.is_card_czar:
            log.logger.debug('player_id %r', self.player_id)
            log.logger.debug(self.game_data)
            players = cache.get('players')
            winner = form.cleaned_data['card_selection']
            log.logger.debug(winner)
            winner_name = players[uuid.UUID(winner)].get('name')
            self.reset(winner_name, uuid.UUID(winner))
            
        else:
            submitted = form.cleaned_data['card_selection']
            # The form returns unicode strings. We want ints in our list.
            self.game_data['submissions'][self.player_id] = [int(card) for card in submitted]
            for card in self.game_data['submissions'][self.player_id]:
                self.player_data['hand'].remove(card)
            log.logger.debug('%r', form.cleaned_data['card_selection'])
        self.write_state()
        log.logger.debug(cache.get('games'))
        return super(PlayerView, self).form_valid(form)

    def write_state(self):
        self.request.session['player_name'] = self.player_name
        self.request.session['game_name'] = self.game_name
        self.game_data['players'][self.player_name] = self.player_data
        games_dict = cache.get('games')
        games_dict[self.game_name] = self.game_data
        cache.set('games', games_dict)

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

    def replace_blanks(self, white_card_num_list, html=False):
        card_text = self.black_card
        if html:
            card_text = cgi.escape(card_text)
        num_blanks = self.black_card.count(blank_marker)
        # assume num_blanks count is valid and len(white_card_num_list) == num_blanks
        if num_blanks == 0:
            card_num = white_card_num_list[0]
            white_text = white_cards[card_num]
            if html:
                white_text = '<strong>' + cgi.escape(white_text) + '</strong>'
            card_text = card_text + ' ' + white_text
        else:
            for card_num in white_card_num_list:
                white_text = white_cards[card_num]
                white_text = white_text.rstrip('.')
                """We can't change the case of the first letter in case
                it is a real name :-( We'd need to consult a word list,
                to make that decision which is way too much effort at
                the moment."""
                if html:
                    white_text = '<strong>' + cgi.escape(white_text) + '</strong>'
                card_text = card_text.replace(blank_marker, white_text, 1)
        return card_text

    def reset(self, winner=None, winner_id=None):
        self.game_data['submissions'] = {}
        self.game_data['current_black_card'] = self.game_data['black_deck'].pop()
        self.game_data['players'][winner]['wins'] += 1
        self.game_data['card_czar'] = winner_id
        num_blanks = black_cards[self.game_data['current_black_card']].count(blank_marker)
        self.game_data['round'] += 1
        self.game_data['last_round_winner'] = winner
        # TODO: Deal Cards 


class LobbyView(FormView):

    template_name = 'lobby.html'
    form_class = GameForm

    def __init__(self, *args, **kwargs):
        self.game_list = cache.get('games')

    # def dispatch(self, request, *args, **kwargs):
        # return super(PlayerView, self).dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('player-view')

    def get_context_data(self, *args, **kwargs):
        context = super(LobbyView, self).get_context_data(*args, **kwargs)
        self.player_id = self.request.session.get('player_id', uuid.uuid1())
        self.request.session['player_id'] = self.player_id
        return context

    def get_form_kwargs(self):
        kwargs = super(LobbyView, self).get_form_kwargs()
        if self.game_list:
            kwargs['game_list'] = [(game, game) for game in self.game_list.keys()]
        return kwargs

    def form_valid(self, form):
        self.player_id = self.request.session.get('player_id')
        player_name = form.cleaned_data['player_name']
        
        # Set the game properties in the cache
        if form.cleaned_data['new_game']:
            game_name = form.cleaned_data['new_game']
            new_game = self.create_game()
            new_game['players'][player_name] = self.create_player()
            new_game['card_czar'] = self.player_id
            games = cache.get('games', {})
            games[form.cleaned_data['new_game']] = new_game
        else:
            game_name = form.cleaned_data.get('game_list')
            games = cache.get('games')
            if not games[game_name]['players'].get(player_name):
                games[game_name]['players'][player_name] = self.create_player()
        cache.set('games', games)

        # Set the player properties in the cache
        players = cache.get('players', {})
        player = players.get(self.player_id, {})
        player['name'] = player_name
        player['game'] = game_name
        players[self.player_id] = player
        cache.set('players', players)

        log.logger.debug(cache.get('players'))
        self.request.session['game_name'] = game_name  # TODO check these should be removed, looks like we still rely on cookie contents for user/game name
        self.request.session['player_name'] = player_name
        self.request.session['player_avatar'] = gravatar_robohash_url(player_name)  # FIXME TODO remove this from cookie too

        return super(LobbyView, self).form_valid(form)

    def create_game(self):
        log.logger.debug("New Game called")
        """Create shuffled decks
        uses built in random, it may be better to plug-in a better
        random init routine and/also consider using
        https://pypi.python.org/pypi/shuffle/

        Also take a look at http://code.google.com/p/gcge/
        """
        shuffled_white = range(len(white_cards))
        random.shuffle(shuffled_white)
        shuffled_black = range(len(black_cards))
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

    def create_player(self):
        log.logger.debug("new player called")
        # Basic data obj for player. Eventually, this will be saved in cache.
        return {
            'hand': [],
            'wins': 0,
        }
