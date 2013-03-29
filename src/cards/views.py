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
#         submissions = [list of player submissions for the round],
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

import os
import json
import random

from django.conf import settings
from django.views.generic import FormView, TemplateView
from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.core.cache import cache
from forms import PlayerForm, GameForm
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


class PlayerView(FormView):

    template_name = 'player.html'
    form_class = PlayerForm

    def __init__(self, *args, **kwargs):
        super(PlayerView, self).__init__(*args, **kwargs)

    def dispatch(self, request, *args, **kwargs):

        # Setup for game and player
        log.logger.debug('%r', self.request.session)
        if not self.request.session.get('game_name') or not self.request.session.get('player_name'):
            return redirect(reverse('lobby-view'))

        self.game_name = self.request.session.get('game_name')
        self.player_name = self.request.session.get('player_name')

        try:
            self.game_data = cache.get('games').get(self.game_name)
        except AttributeError:
            return redirect(reverse('lobby-view'))
        if not self.game_data:
            return redirect(reverse('lobby-view'))
        self.player_data = self.game_data['players'].get(self.player_name)

        # Deal hand if player doesn't have one.
        log.logger.debug('%r', self.player_data)
        if not self.player_data['hand']:
            self.player_data['hand'] = [
                self.game_data['white_deck'].pop() for x in xrange(10)
            ]

        # Deal black card if game doesn't have one.
        # FIXME: Game setup.
        if not self.game_data['current_black_card']:
            self.game_data['current_black_card'] = self.game_data['black_deck'].pop()
        pprint(self.game_data['players'])
        self.write_player()
        return super(PlayerView, self).dispatch(request, *args, **kwargs)


    def get_success_url(self):
        return reverse('player-view')

    def get_context_data(self, *args, **kwargs):

        context = super(PlayerView, self).get_context_data(*args, **kwargs)

        self.black_card = black_cards[self.game_data['current_black_card']]
        num_blanks = self.black_card.count(blank_marker)
        context['black_card'] = self.black_card.replace(blank_marker, '______')
        context['player_name'] = self.player_name
        context['game_name'] = self.game_name

        # Display filled-in answer if player has submitted.
        if self.player_data.get('submitted'):

            # Replacing the blank marker with %s lets us do cool stuff below
            black_string = self.black_card.replace('%', '%%')
            black_string = black_string.replace(blank_marker, '%s')
            context['submission'] = [
                white_cards[int(card)] for card in self.player_data['submitted']
            ]

            # For some reason, need to pull get the strings out first, then strip the period.
            answer_strings = [white_cards[card] for card in self.player_data['submitted']]
            answer_list = tuple([answer.rstrip('.') for answer in answer_strings])

            # single white card replacement
            if num_blanks == 0:
                filled_in_question = '%s %s' % (self.black_card, white_cards[self.player_data['submitted'][0]])  # FIXME newline prettyness
            # More than one white card.
            else:
                filled_in_question = black_string % answer_list

            context['filled_in_question'] = filled_in_question

        context['action'] = reverse('player-view')
        return context

    def get_form_kwargs(self):
        kwargs = super(PlayerView, self).get_form_kwargs()
        kwargs['blanks'] = black_cards[self.game_data['current_black_card']].count(blank_marker) or 1
        kwargs['cards'] = tuple(
            (card, white_cards[card]) for card in self.player_data['hand']
        )
        return kwargs

    def form_valid(self, form):
        submitted = form.cleaned_data['card_selection']

        # The form returns unicode strings. We want ints in our list.
        self.player_data['submitted'] = [int(card) for card in submitted]
        for card in self.player_data['submitted']:
            self.player_data['hand'].remove(card)
        self.write_player()
        log.logger.debug('%r', form.cleaned_data['card_selection']) 
        return super(PlayerView, self).form_valid(form)

    def write_player(self):
        self.request.session['player_name'] = self.player_name
        self.request.session['game_name'] = self.game_name
        self.game_data['players'][self.player_name] = self.player_data
        games_dict = cache.get('games')
        try:
            games_dict[self.game_name] = self.game_data
        except TypeError:
            games_dict = {self.game_name: self.game_data}
        cache.set('games', games_dict)

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
        self.player_id = self.request.session.get('player_id')
        if not self.player_id:
            self.player_id = uuid.uuid1()
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
        players = cache.get('players', {})
        player = players.get(self.player_id, {})
        player['name'] = player_name
        cache.set('players', players)
        if form.cleaned_data['new_game']:
            game_name = form.cleaned_data['new_game']
            new_game = self.create_game()
            new_game['players'][player_name] = self.create_player()
            games = cache.get('games', {})
            games[form.cleaned_data['new_game']] = new_game
            cache.set('games', games)
        else:
            game_name = form.cleaned_data.get('game_list')
            games = cache.get('games')
            if not games[game_name]['players'].get(player_name):
                games[game_name]['players'][player_name] = self.create_player()
            cache.set('games', games)

        self.request.session['game_name'] = game_name
        self.request.session['player_name'] = player_name

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
            'submissions': [],
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
