# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#

from django.utils.safestring import mark_safe
from django.views.generic import FormView
from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.core.cache import cache

from forms import PlayerForm, LobbyForm, CzarForm, JoinForm
from models import BlackCard, WhiteCard, Game, BLANK_MARKER, GAMESTATE_SUBMISSION, GAMESTATE_SELECTION, avatar_url

import log


class LobbyView(FormView):

    template_name = 'lobby.html'
    form_class = LobbyForm

    def __init__(self, *args, **kwargs):
        self.game_list = Game.objects.filter(is_active=True).values_list('id', 'name')

    # FIXME remove this method
    def dispatch(self, request, *args, **kwargs):
        return super(LobbyView, self).dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('game-join-view', kwargs={'pk': self.game.id})

    def get_context_data(self, *args, **kwargs):
        context = super(LobbyView, self).get_context_data(*args, **kwargs)
        context['joinable_game_list'] = self.game_list  # TODO rename?

        context['show_form'] = True

        return context

    def get_form_kwargs(self):
        kwargs = super(LobbyView, self).get_form_kwargs()
        if self.game_list:
            kwargs['game_list'] = [name for _, name in self.game_list]
        return kwargs

    def form_valid(self, form):
        session_details = self.request.session.get('session_details', {})  # FIXME
        # FIXME if not a dict, make it a dict (upgrade old content)
        log.logger.debug('session_details %r', session_details)

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
                tmp_game.gamedata = new_game
                tmp_game.save()
                self.game = tmp_game
        if existing_game:
            if not game_name:
                game_name = form.cleaned_data.get('game_list')
            existing_game = Game.objects.get(name=game_name)  # existing_game maybe a bool
            log.logger.debug('existing_game %r', (game_name, player_name,))
            log.logger.debug('existing_game.gamedata %r', (existing_game.gamedata,))
            log.logger.debug('existing_game.gamedata players %r', (existing_game.gamedata['players'],))
            existing_game.save()

        # Set the player session details
        session_details = {}
        #session_details['name'] = player_name
        session_details['game'] = game_name
        self.request.session['session_details'] = session_details  # this is probably kinda dumb.... Previously we used seperate session items for game and user name and that maybe what we need to go back to

        return super(LobbyView, self).form_valid(form)


class GameView(FormView):

    template_name = 'game_view.html'
    form_class = PlayerForm

    def dispatch(self, request, *args, **kwargs):
        log.logger.debug('%r %r', args, kwargs)
        game = Game.objects.get(pk=kwargs['pk'])

        player_name = None
        session_details = self.request.session.get('session_details')
        # TODO username determination should be a shared function, called by GameView() and GameJoinView()
        if self.request.user.is_authenticated():
            player_name = self.request.user.username
            if player_name and player_name not in game.gamedata['players']:
                # check session name next
                player_name = None
        
        if player_name is None:
            # Assume AnonymousUser
            if session_details:
                player_name = session_details['name']
            else:
                player_name = None  # observer
        if player_name and player_name not in game.gamedata['players']:
            player_name = None

        card_czar_name = game.gamedata['card_czar']
        is_card_czar = player_name == card_czar_name

        self.player_name = player_name
        self.game = game
        self.is_card_czar = is_card_czar
        return super(GameView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super(GameView, self).get_context_data(*args, **kwargs)
        log.logger.debug('context%r', context)
        game = self.game
        player_name = self.player_name
        is_card_czar = self.is_card_czar

        log.logger.debug('game %r', game.gamedata['players'])
        black_card_id = game.gamedata['current_black_card']
        black_card = BlackCard.objects.get(id=black_card_id)
        context['show_form'] = self.can_show_form()
        context['refresh_num_secs'] = 20  # something high for debugging FIXME make this either settings variable (or database admin view changeable)
        context['game'] = game
        context['black_card'] = black_card.text.replace(BLANK_MARKER, '______')  # FIXME roll this into BlackCard.replace_blanks()

        card_czar_name = game.gamedata['card_czar']
        context['card_czar_name'] = card_czar_name
        context['card_czar_avatar'] = game.gamedata['players'][card_czar_name]['player_avatar']

        player_name = self.player_name
        if player_name:
            white_cards_text_list = [mark_safe(card_text) for card_text, in WhiteCard.objects.filter(id__in=game.gamedata['players'][player_name]['hand']).values_list('text')]
            context['white_cards_text_list'] = white_cards_text_list
            
            if game.gamedata['submissions'] and not is_card_czar:
                player_submission = game.gamedata['submissions'].get(player_name)
                if player_submission:
                    context['filled_in_question'] = black_card.replace_blanks(player_submission) 

        # at this point if player_name is None, they are an observer
        # otherwise a (supposedly) active player

        context['is_card_czar'] = is_card_czar
        context['player_name'] = player_name
        if player_name:
            context['player_avatar'] = game.gamedata['players'][player_name]['player_avatar']

        return context

    def get_success_url(self):
        return reverse('game-view', kwargs={'pk': self.game.id})

    def form_valid(self, form):
        game = self.game
        player_name = self.player_name
        is_card_czar = self.is_card_czar

        if is_card_czar:
            winner = form.cleaned_data['card_selection']
            log.logger.debug(winner)
            winner = winner[0]  # for some reason we have a list
            winner_name = winner
            log.logger.debug('start new round %r %r %r', player_name, winner_name, winner)
            game.start_new_round(player_name, winner_name, winner)
        else:
            submitted = form.cleaned_data['card_selection']
            # The form returns unicode strings. We want ints in our list.
            white_card_list = [int(card) for card in submitted]
            log.logger.debug("white_card_list; %r", white_card_list)
            game.submit_white_cards(player_name, white_card_list)  # FIXME catch GameError and/or check before hand
            if game.gamedata['filled_in_texts']:
                log.logger.debug('filled_in_texts %r', game.gamedata['filled_in_texts'])
            log.logger.debug('%r', form.cleaned_data['card_selection'])
        game.save()
        return super(GameView, self).form_valid(form)

    def get_form_kwargs(self):
        game = self.game
        player_name = self.player_name
        is_card_czar = self.is_card_czar

        black_card_id = game.gamedata['current_black_card']
        kwargs = super(GameView, self).get_form_kwargs()
        if player_name:
            # get_form_kwargs() is called all the time even when we don't intend to show form
            # check above could be can_show_form()?
            if is_card_czar:
                if game.game_state == GAMESTATE_SELECTION:
                    czar_selection_options = [
                        (player_id, mark_safe(filled_in_card)) for player_id, filled_in_card in game.gamedata['filled_in_texts']
                    ]
                    kwargs['cards'] = czar_selection_options
            else:
                temp_black_card = BlackCard.objects.get(id=black_card_id)
                kwargs['blanks'] = temp_black_card.pick
                cards = [(card_id, mark_safe(card_text)) for card_id, card_text in WhiteCard.objects.filter(id__in=game.gamedata['players'][player_name]['hand']).values_list('id', 'text')]
                kwargs['cards'] = cards
        return kwargs

    # internal utiltity methods

    def can_show_form(self):
        result = False
        
        if self.player_name:
            if self.is_card_czar:
                if self.game.game_state == GAMESTATE_SELECTION:
                    # show czar pick winner submission form
                    result = True
            else:
                if self.game.game_state == GAMESTATE_SUBMISSION and self.game.gamedata['submissions'].get(self.player_name) is None:
                    # show white card submission form
                    result = True
        return result


class GameJoinView(FormView):
    """This is a temp function that expects a user already exists and is logged in,
    then joins them to an existing game.

    We want to support real user accounts but also anonymous, which is why
    this is a debug routine for now.

    TODO password protection check on join.
    TODO create a game (with no players, redirect to join game for game creator).
    """

    template_name = 'game_join.html'
    form_class = JoinForm

    def dispatch(self, request, *args, **kwargs):
        log.logger.debug('%r %r', args, kwargs)
        game = Game.objects.get(pk=kwargs['pk'])  # FIXME this wil fail to non existent game
        request = self.request
        
        self.request = request
        self.game = game
        
        player_name = None
        
        if request.user.is_authenticated():
            player_name = request.user.username
            player_image_url = avatar_url(request.user.email)
        else:
            # Assume AnonymousUser
            # also assume the set a name earlier....
            session_details = request.session.get('session_details')
            if session_details:
                player_name = session_details.get('name')
                if player_name:
                    player_image_url = avatar_url(player_name)
        
        if player_name:
            if player_name not in game.gamedata['players']:
                game.add_player(player_name, player_image_url=player_image_url)
                if len(game.gamedata['players']) == 1:
                    game.start_new_round(winner_id=player_name)
                game.save()
        
            log.logger.debug('about to return reverse')
            return redirect(reverse('game-view', kwargs={'pk': game.id}))
        
        return super(GameJoinView, self).dispatch(request, *args, **kwargs)
        

    def get_context_data(self, *args, **kwargs):
        context = super(GameJoinView, self).get_context_data(*args, **kwargs)
        context['show_form'] = True
        log.logger.debug('context %r', context)
        # if we are here we need a player name (or they need to log in so we can get a player name)
        # TODO and maybe a password
        #request = self.request
        #game = self.game
        
        return context
        
    def get_success_url(self):
        return reverse('game-join-view', kwargs={'pk': self.game.id})

    def form_valid(self, form):
        player_name = form.cleaned_data['player_name']
        session_details = {}
        session_details['name'] = player_name
        self.request.session['session_details'] = session_details
        return super(GameJoinView, self).form_valid(form)

#######################


def debug_deactivate_old_games(request):
    Game.deactivate_old_games()
    return redirect('/')  # DEBUG just so it doesn't error out
