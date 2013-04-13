# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#

# Contract between LobbyView and PlayerView:
#
# LobbyView will give PlayerView a named player and a game stored in database.
# PlayerView will return to LobbyView any request that does not have those things.

import random
import uuid

from django.utils.safestring import mark_safe
from django.views.generic import FormView, DetailView
from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.core.cache import cache

from forms import PlayerForm, GameForm, CzarForm
from models import BlackCard, WhiteCard, Game, BLANK_MARKER, GAMESTATE_SUBMISSION

import log


class PlayerView(FormView):

    template_name = 'player.html'
    form_class = PlayerForm

    def __init__(self, *args, **kwargs):
        super(PlayerView, self).__init__(*args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        # Setup for game and player

        session_details = self.request.session.get('session_details', {})  # FIXME
        # FIXME if not a dict, make it a dict (upgrade content)
        log.logger.debug('session_details %r', session_details)
        if not session_details:
            return redirect(reverse('lobby-view'))

        # TODO Player model lookup
        self.game_name = session_details['game']  # TODO start using game number id (not name)
        self.player_name = session_details['name']
        self.player_id = self.player_name  # FIXME needless duplicatation that needs to be refactored, this may become player number

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

        # FIXME additional db IO :-( TODO cache unnormalized data in game?
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
            winner = form.cleaned_data['card_selection']
            log.logger.debug(winner)
            winner_name = winner
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
        print 'DEBUG context', context
        self.player_counter = cache.get('player_counter', 0) + 1
        cache.set('player_counter', self.player_counter)
        context['player_counter'] = self.player_counter

        context['show_form'] = True
        
        session_details = self.request.session.get('session_details', {})  # FIXME
        # FIXME if not a dict, make it a dict (upgrade old content)
        log.logger.debug('session_details %r', session_details)

        self.player_id = session_details.get('name')
        if isinstance(self.player_id, uuid.UUID):
            # NOTE this "fixes" and upgrades session data for old clients
            # we shouldn't have any of these in the wild so this code should be REMOVED
            # This is here to help with initial internal testing
            self.player_id = None
            # TODO test do we need to explictly set the session entry (dict's don't tend to need this)
        if not self.player_id:
            # TODO this may become player number (not name)
            
            # For now we auto generate a name (setting username needs to be done in a form)
            self.player_id = 'Auto Player %d' % self.player_counter  # this is currently a NOOP
            session_details['name'] = self.player_id
            self.request.session['session_details'] = session_details  # this is probably kinda dumb.... Previously we used seperate session items for game and user name and that maybe what we need to go back to
        log.logger.debug('self.player_id %r', self.player_id)

        return context

    def get_form_kwargs(self):
        kwargs = super(LobbyView, self).get_form_kwargs()
        if self.game_list:
            kwargs['game_list'] = self.game_list
        kwargs['player_counter'] = self.player_counter
        return kwargs

    def form_valid(self, form):
        session_details = self.request.session.get('session_details', {})  # FIXME
        # FIXME if not a dict, make it a dict (upgrade old content)
        log.logger.debug('session_details %r', session_details)

        """
        if session_details:
            # FIXME this will break new game creation.....
            raise NotImplementedError('attempting to join a game when player is already in a game')
        """

        player_name = form.cleaned_data['player_name']
        self.player_id = player_name  # FIXME needless duplicatation that needs to be refactored, this may become player number

        existing_game = True
        # Set the game properties in the database and session
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

        # Set the player session details
        session_details['name'] = player_name
        session_details['game'] = game_name
        self.request.session['session_details'] = session_details  # this is probably kinda dumb.... Previously we used seperate session items for game and user name and that maybe what we need to go back to


        return super(LobbyView, self).form_valid(form)


class GameView(DetailView):

    model = Game
    template_name = 'game_view.html'

    def get_context_data(self, *args, **kwargs):
        session_details = self.request.session['session_details']  # hard fail for now on lookup failure, FIXME for observers
        context = super(GameView, self).get_context_data(*args, **kwargs)
        game = context['object']
        black_card_id = game.gamedata['current_black_card']
        black_card = BlackCard.objects.get(id=black_card_id)
        context['show_form'] = True  # FIXME temp hack to avoid browser auto refresh
        context['game'] = game
        context['black_card'] = black_card.text.replace(BLANK_MARKER, '______')  # FIXME roll this into BlackCard.replace_blanks()
        
        card_czar_name = game.gamedata['card_czar']
        context['card_czar_name'] = card_czar_name
        context['card_czar_avatar'] = game.gamedata['players'][card_czar_name]['player_avatar']
        
        player_name = None
        if self.request.user.is_authenticated():
            player_name = self.request.user.email
        else:
            # Assume AnonymousUser
            if session_details:
                player_name = session_details['name']
        if player_name and player_name not in game.gamedata['players']:
            player_name = None
        # at this point if player_name is None, they are an observer
        # otherwise a (supposedly) active player

        is_card_czar = player_name == card_czar_name
        context['is_card_czar'] = is_card_czar
        
        """TODO determine if user is:
            observer - show current state of play
            card czar (show waiting for players OR select winner)
            white card player (select card(s) OR waiting for other white card players OR all submitted white cards)
        """

        return context


def debug_join(request, pk):
    """This is a temp function that expects a user already exists and is logged in,
    then joins them to a game.
    
    We want to support real user accounts but also anonymous, which is why
    this is a debug routine for now.
    """
    log.logger.debug('request.user %s', request.user)
    game = Game.objects.get(id=pk)
    if request.user.is_authenticated():
        player_name = request.user.email  # or perhaps use name and set avatar to email....
    else:
        # Assume AnonymousUser
        # also assume the set a name earlier....
        session_details = request.session['session_details']
        existing_game_name = session_details['game']  # FIXME now use this and check it...
        player_name = session_details['name']
    if player_name not in game.gamedata['players']:
        game.gamedata['players'][player_name] = game.create_player(player_name)
        game.save()
    #redirect(reverse('game-view'))
    return redirect('.')  # FIXME .. please! :-(
