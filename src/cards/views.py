# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#

import json
import os
from django.conf import settings
from django.views.generic import FormView, TemplateView
from django.core.urlresolvers import reverse
from django.core.cache import cache
from forms import PlayerForm
from game import Game

class PlayerView(FormView):

    template_name = 'player.html'
    form_class = PlayerForm
    game_name = 'game1'

    cards = ((1,'1'),(2, '2'))

    def __init__(self, *args, **kwargs):
        if not cache.get('global_blacks'):
            self.game_init()
        self.global_whites = cache.get('global_whites')
        self.global_blacks = cache.get('global_blacks')
        super(PlayerView, self).__init__(*args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        self.create_game()
        self.game = cache.get('games')[self.game_name]
        self.request.session['player_name'] = 'player1'
        self.read_player()
        return super(PlayerView, self).dispatch(request, *args, **kwargs)


    def get_success_url(self):
        return reverse('player-view')

    def get_context_data(self, **kwargs):
        context = super(PlayerView, self).get_context_data(**kwargs)

        context['name_from_session'] = self.request.session.get('player_name', '')
        self.is_card_czar = context['is_card_czar'] = self.player['is_card_czar'] == 1
        context['player_name'] = self.name
        context['selected'] = self.player['selected']
        return context

    def get_form_kwargs(self):
        kwargs = super(PlayerView, self).get_form_kwargs()
        kwargs['cards'] = tuple((card, self.global_whites[card]) for card in self.player['hand'])
        return kwargs

    def form_valid(self, form):
        self.player['selected'] = form.cleaned_data['card_selection']
        # self.write_player()
        print form.cleaned_data['card_selection']
        return super(PlayerView, self).form_valid(form)

    def read_player(self):
        self.name = self.request.session['player_name']
        self.player = self.game['players'][self.name]

    def write_player(self):
        with open(os.path.join(settings.PROJECT_ROOT, 'player.json'), 'w') as data:
            data.write(json.dumps(self.player))

    def game_init(self):
        with open(os.path.join(settings.PROJECT_ROOT, 'data/data.json')) as data:
            cards = json.loads(data.read())
            cache.set('global_blacks', cards['black_cards'], 3600)
            cache.set('global_whites', cards['white_cards'], 3600)

    def create_game(self):
        games = {
            'game1':{
                'players': {
                    'player1': {
                        'hand': [1,2,3],
                        'is_card_czar': False,
                        'wins': 0,
                        'selected': 1
                    }
                }
            }
        }
        cache.set('games', games)

class GameView(FormView):

    template_name = 'player.html'
    form_class = PlayerForm

    # def get_form_kwargs


class LobbyView(TemplateView):

    template_name = 'lobby.html'
