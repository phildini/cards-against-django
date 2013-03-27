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
#         current_black_card = '',
#         submissions = [list of player submissions for the round],
#         round: int,
#         card_czar = 'player1',
#         black_deck = [],
#         white_deck = [],
#     },
#     game2 {...},
#     ...
# }

import os
import json
import random

from django.conf import settings
from django.views.generic import FormView, TemplateView
from django.core.urlresolvers import reverse
from django.core.cache import cache
from forms import PlayerForm
from game import Game

# Grab data from the cards json and set global, unaltered decks.
with open(os.path.join(settings.PROJECT_ROOT, 'data/data.json')) as data:
    cards = json.loads(data.read())
    black_cards = cards['black_cards']
    white_cards = cards['white_cards']

class PlayerView(FormView):

    template_name = 'player.html'
    form_class = PlayerForm

    # Currently placeholders. Evnetually, will get from player.
    game_name = 'game1'
    player_name = 'player1'

    def __init__(self, *args, **kwargs):
        super(PlayerView, self).__init__(*args, **kwargs)

    def dispatch(self, request, *args, **kwargs):

        # Setup for game and player
        # Attempt to pull game from cache based on cookie. If not, create game.
        if not self.request.session.get('game_name'):
            self.game_data = self.create_game(self.game_name)
            self.request.session['game_name'] = self.game_name
        else:
            try:
                self.game_data = cache.get('games').get(game_name)
            except AttributeError:
                self.game_data = self.create_game(self.game_name)

        # Attempt to pull player from cache, if not create.
        if not self.request.session.get('player_name'):
            self.player_data = self.create_player(self.player_name)
            self.game_data['players'][self.player_name] = self.player_data
        else:
            self.player_data = self.game_data.get('players')
            if self.player_data:
                self.player_data = self.game_data.get('players').get('player_name')
            else:
                self.player_data = self.create_player(self.player_name)
                self.game_data['players'][self.player_name] = self.player_data

        # Deal hand if player doesn't have one.
        if not self.player_data['hand']:
            self.player_data['hand'] = [
                self.game_data['white_deck'].pop() for x in xrange(10)
            ]

        return super(PlayerView, self).dispatch(request, *args, **kwargs)


    def get_success_url(self):
        return reverse('player-view')

    def get_context_data(self, **kwargs):
        context = super(PlayerView, self).get_context_data(**kwargs)

        context['player_name'] = self.player_name
        context['submission'] = self.player_data['submission']
        return context

    def get_form_kwargs(self):
        kwargs = super(PlayerView, self).get_form_kwargs()
        kwargs['cards'] = tuple(
            (card, card) for card in self.player_data['hand']
        )
        return kwargs

    def form_valid(self, form):
        self.player['selected'] = form.cleaned_data['card_selection']
        # self.write_player()
        print form.cleaned_data['card_selection']
        return super(PlayerView, self).form_valid(form)

    def write_player(self):
        with open(os.path.join(settings.PROJECT_ROOT, 'player.json'), 'w') as data:
            data.write(json.dumps(self.player))

    def create_game(self, game_name):

        # Create shuffled decks
        shuffled_white = white_cards
        random.shuffle(shuffled_white)
        shuffled_black = black_cards
        random.shuffle(shuffled_black)

        # Basic data object for a game. Eventually, this will be saved in cache.
        return {
            'players': {},
            'current_black_card': 0,
            'submissions': [],
            'round': 0,
            'card_czar': '',
            'white_deck': shuffled_white,
            'black_deck': shuffled_black,
            'mode': 'submitting',
        }

    def create_player(self, player_name):

        # Basic data obj for player. Eventually, this will be saved in cache.
        return {
            'hand': [],
            'wins': 0,
            'submission': 0,
        }

class LobbyView(TemplateView):

    template_name = 'lobby.html'
