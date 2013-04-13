# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#

# Contract between LobbyView and PlayerView:
#
# LobbyView will give PlayerView a named player and a game stored in cache.
# PlayerView will return to LobbyView any request that does not have those things.
# On the cache, 'players' will hav a mapping of ids to players.

import random
import uuid

from django.utils.safestring import mark_safe
from django.views.generic import FormView, DetailView
from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.core.cache import cache

from forms import PlayerForm, GameForm, CzarForm
from models import BlackCard, WhiteCard, Game, BLANK_MARKER

import log


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
            # FIXME call start_new_round, do not manually deal black card here; what if the black card is a "draw 3, pick 2" card.
            self.game_data['current_black_card'] = self.game_dbobj.deal_black_card()
        self.write_state()

        if self.is_card_czar:
            self.form_class = CzarForm
        return super(PlayerView, self).dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('player-view')

    def get_context_data(self, *args, **kwargs):
        context = super(PlayerView, self).get_context_data(*args, **kwargs)
        context['game'] = self.game_dbobj

        # FIXME additional db IO :-( TODO cache in game?
        black_card_id = self.game_data['current_black_card']
        temp_black_card = BlackCard.objects.get(id=black_card_id)

        context['players'] = self.game_data['players']
        last_round_winner = self.game_data.get('last_round_winner', '')
        context['last_round_winner'] = last_round_winner
        if last_round_winner:
            context['last_round_winner_avatar'] = self.game_data['players'][last_round_winner]['player_avatar']
        context['black_card'] = self.black_card.replace(BLANK_MARKER, '______')  # FIXME roll this into BlackCard.replace_blanks()
        context['player_name'] = self.player_name
        context['player_avatar'] = self.game_data['players'][self.player_name]['player_avatar']
        context['game_name'] = self.game_name
        context['show_form'] = self.can_show_form()
        # Display filled-in answer if player has submitted.
        if self.game_data['submissions'] and not self.is_card_czar:
            player_submission = self.game_data['submissions'][self.player_id]
            context['filled_in_question'] = temp_black_card.replace_blanks(player_submission)
        context['action'] = reverse('player-view')
        return context

    def get_form_kwargs(self):
        black_card_id = self.game_data['current_black_card']
        temp_black_card = BlackCard.objects.get(id=black_card_id)
        black_card_text = temp_black_card.text
        self.black_card = black_card_text
        kwargs = super(PlayerView, self).get_form_kwargs()
        if self.is_card_czar:
            czar_selection_options = [
                (player_id, mark_safe(temp_black_card.replace_blanks(self.game_data['submissions'][player_id]))) for player_id in self.game_data['submissions']
            ]
            random.shuffle(czar_selection_options)
            kwargs['cards'] = czar_selection_options
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
            self.game_dbobj.start_new_round(self.player_name, winner_name, winner)

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


class LobbyView(FormView):

    template_name = 'lobby.html'
    form_class = GameForm

    def __init__(self, *args, **kwargs):
        self.game_list = Game.objects.filter(is_active=True).values_list('name', 'name')
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
                tmp_game = Game(name=form.cleaned_data['new_game'])
                new_game = tmp_game.create_game()
                new_game['players'][player_name] = tmp_game.create_player(player_name)
                new_game['card_czar'] = self.player_id
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
                existing_game.gamedata['players'][player_name] = existing_game.create_player(player_name)
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


class GameView(DetailView):

    model = Game
    template_name = 'game_view.html'

    def get_context_data(self, *args, **kwargs):
        context = super(GameView, self).get_context_data(*args, **kwargs)
        game = context['object']
        black_card_id = game.gamedata['current_black_card']
        black_card = BlackCard.objects.get(id=black_card_id)
        context['show_form'] = True  # FIXME temp hack to avoid browser auto refresh
        context['game'] = game
        context['black_card'] = black_card.text.replace(BLANK_MARKER, '______')  # FIXME roll this into BlackCard.replace_blanks()
        
        """TODO determine if user is:
            observer - show current state of play
            card czar (show waiting for players OR select winner)
            white card player (select card(s) OR waiting for other white card players OR all submitted white cards)
        """
        context['card_czar_name'] = game.gamedata['card_czar']

        return context


def debug_join(request, pk):
    """This is a temp function that expects a user already exists and is logged in,
    then joins them to a game.
    
    We want to support real user accounts but also anonymous, which is why
    this is a debug routine for now.
    """
    assert(request.user.is_authenticated())
    game = Game.objects.get(id=pk)
    if request.user.email not in game.gamedata['players']:
        player_name = request.user.email  # or perhaps use name and set avatar to email....
        game.gamedata['players'][player_name] = game.create_player(player_name)
        game.save()
    #redirect(reverse('game-view'))
    return redirect('.')  # FIXME .. please! :-(
