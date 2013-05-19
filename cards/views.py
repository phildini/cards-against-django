# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#

import json

from django.http import Http404, HttpResponse
from django.utils.safestring import mark_safe
from django.views.generic import FormView
from django.views.generic.base import View
from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.conf import settings

from forms import (
    PlayerForm,
    LobbyForm,
    JoinForm,
    ExitForm,
)

from models import (
    BlackCard,
    WhiteCard,
    Game,
    BLANK_MARKER,
    GAMESTATE_SUBMISSION,
    GAMESTATE_SELECTION,
    avatar_url,
)

import log
if settings.USE_PUSHER:
    import pusher


class GameViewMixin(object):
    def get_game(self, game_id):
        """Returns a game object for a given id

        Raises Http404 if the game does not exist.
        """

        if not hasattr(self, '_games'):
            self._games = {}

        if game_id not in self._games:
            try:
                self._games[game_id] = Game.objects.get(pk=game_id)
            except Game.DoesNotExist:
                raise Http404

        return self._games[game_id]

    def get_player_name(self):
        player_name = None

        if self.request.user.is_authenticated():
            player_name = self.request.user.username

        if not player_name:
            # Assume AnonymousUser
            session_details = self.request.session.get('session_details')
            if session_details:
                player_name = session_details.get('name')
            else:
                player_name = None  # observer

        if player_name and player_name not in self.game.gamedata['players']:
            player_name = None

        return player_name


class LobbyView(FormView):

    template_name = 'lobby.html'
    form_class = LobbyForm

    def __init__(self, *args, **kwargs):
        self.game_list = Game.objects.filter(
            is_active=True
        ).values_list('id', 'name')

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
                new_game = tmp_game.create_game(form.cleaned_data['card_set'])
                tmp_game.gamedata = new_game
                tmp_game.save()
                self.game = tmp_game

        if existing_game:
            if not game_name:
                game_name = form.cleaned_data.get('game_list')

            existing_game = Game.objects.get(name=game_name)  # existing_game maybe a bool

            log.logger.debug('existing_game.gamedata %r',
                (existing_game.gamedata,)
            )
            log.logger.debug('existing_game.gamedata players %r',
                (existing_game.gamedata['players'],)
            )

            existing_game.save()

        # Set the player session details
        session_details['game'] = game_name
        self.request.session['session_details'] = session_details  # this is probably kinda dumb.... Previously we used seperate session items for game and user name and that maybe what we need to go back to

        return super(LobbyView, self).form_valid(form)


class GameView(GameViewMixin, FormView):

    template_name = 'game_view.html'
    form_class = PlayerForm

    def dispatch(self, request, *args, **kwargs):
        log.logger.debug('%r %r', args, kwargs)
        self.game = self.get_game(kwargs['pk'])

        if self.game.deactivate_old_game():
            self.game.save()

        self.player_name = self.get_player_name()

        card_czar_name = self.game.gamedata['card_czar']
        self.is_card_czar = self.player_name == card_czar_name

        return super(GameView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super(GameView, self).get_context_data(*args, **kwargs)
        log.logger.debug('context%r', context)

        log.logger.debug('game %r', self.game.gamedata['players'])
        black_card_id = self.game.gamedata['current_black_card']
        black_card = BlackCard.objects.get(id=black_card_id)

        context['show_form'] = self.can_show_form()
        if self.game.game_state == GAMESTATE_SELECTION:
            context['refresh_num_secs'] = 60  # FIXME make this either settings variable (or database admin view changeable)
        else:
            context['refresh_num_secs'] = 60  # FIXME make this either settings variable (or database admin view changeable)

        context['game'] = self.game
        context['black_card'] = black_card.text.replace(BLANK_MARKER, '______')  # FIXME roll this into BlackCard.replace_blanks()

        card_czar_name = self.game.gamedata['card_czar']
        context['card_czar_name'] = card_czar_name
        context['card_czar_avatar'] = self.game.gamedata['players'][card_czar_name]['player_avatar']

        if self.player_name:
            white_cards_text_list = [
                mark_safe(card_text)
                for card_text,
                in WhiteCard.objects.filter(
                    id__in=self.game.gamedata['players'][self.player_name]['hand']
                ).values_list('text')
            ]
            context['white_cards_text_list'] = white_cards_text_list

            if self.game.gamedata['submissions'] and not self.is_card_czar:
                player_submission = self.game.gamedata['submissions'].get(self.player_name)
                if player_submission:
                    context['filled_in_question'] = black_card.replace_blanks(
                        player_submission
                    )

        # at this point if player_name is None, they are an observer
        # otherwise a (supposedly) active player

        context['is_card_czar'] = self.is_card_czar
        context['player_name'] = self.player_name
        if self.player_name:
            context['player_avatar'] = self.game.gamedata['players'][self.player_name]['player_avatar']
        if settings.USE_PUSHER:
            context['pusher_key'] = settings.PUSHER_KEY

        context['use_pusher'] = settings.USE_PUSHER

        return context

    def get_success_url(self):
        return reverse('game-view', kwargs={'pk': self.game.id})

    def form_valid(self, form):
        if self.is_card_czar:
            winner = form.cleaned_data['card_selection']
            log.logger.debug(winner)
            winner = winner[0]  # for some reason we have a list
            winner_name = winner
            log.logger.debug(
                'start new round %r %r %r',
                self.player_name,
                winner_name,
                winner
            )
            self.game.start_new_round(self.player_name, winner_name, winner)
        else:
            submitted = form.cleaned_data['card_selection']
            # The form returns unicode strings. We want ints in our list.
            white_card_list = [int(card) for card in submitted]
            log.logger.debug("white_card_list; %r", white_card_list)
            self.game.submit_white_cards(self.player_name, white_card_list)  # FIXME catch GameError and/or check before hand

            if self.game.gamedata['filled_in_texts']:
                log.logger.debug(
                    'filled_in_texts %r',
                    self.game.gamedata['filled_in_texts']
                )
            log.logger.debug('%r', form.cleaned_data['card_selection'])
        self.game.save()

        if settings.USE_PUSHER:
            instance = pusher.Pusher(
                app_id=settings.PUSHER_APP_ID,
                key=settings.PUSHER_KEY,
                secret=settings.PUSHER_SECRET
            )
            instance['my-channel'].trigger(
                'my-event',
                {
                    'message': 'hello world'
                }
            )
        return super(GameView, self).form_valid(form)

    def get_form_kwargs(self):
        black_card_id = self.game.gamedata['current_black_card']
        kwargs = super(GameView, self).get_form_kwargs()
        if self.player_name:
            # get_form_kwargs() is called all the time even when we don't intend to show form
            # check above could be can_show_form()?
            if self.is_card_czar:
                if self.game.game_state == GAMESTATE_SELECTION:
                    czar_selection_options = [
                        (player_id, mark_safe(filled_in_card))
                        for player_id, filled_in_card
                        in self.game.gamedata['filled_in_texts']
                    ]
                    kwargs['cards'] = czar_selection_options
            else:
                temp_black_card = BlackCard.objects.get(id=black_card_id)
                kwargs['blanks'] = temp_black_card.pick
                cards = [
                    (card_id, mark_safe(card_text))
                    for card_id, card_text
                    in WhiteCard.objects.filter(
                        id__in=self.game.gamedata['players'][self.player_name]['hand']
                    ).values_list('id', 'text')
                ]
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
                if (self.game.game_state == GAMESTATE_SUBMISSION and
                    not self.game.gamedata['submissions'].get(self.player_name)
                ):
                    # show white card submission form
                    result = True
        return result


class GameCheckReadyView(GameViewMixin, View):
    def get_context_data(self, *args, **kwargs):
        context = {
            'game_id': self.game.id,
            'isReady': False,
        }

        return context

    def get(self, request, *args, **kwargs):
        self.game = self.get_game(kwargs['pk'])

        return HttpResponse(
            json.dumps(self.get_context_data()),
            mimetype="application/json"
        )


class GameExitView(GameViewMixin, FormView):
    template_name = 'game_exit.html'
    form_class = ExitForm

    def dispatch(self, request, *args, **kwargs):
        log.logger.debug('%r %r', args, kwargs)
        self.game = self.get_game(kwargs['pk'])
        self.player_name = self.get_player_name()

        if self.player_name:
            if self.player_name in self.game.gamedata['players']:
                return super(GameExitView, self).dispatch(
                    request,
                    *args,
                    **kwargs
                )
        return redirect(reverse('game-view', kwargs={'pk': self.game.id}))

    def get_context_data(self, *args, **kwargs):
        context = super(GameExitView, self).get_context_data(*args, **kwargs)
        context['show_form'] = True
        return context

    def get_success_url(self):
        return reverse('game-view', kwargs={'pk': self.game.id})

    def form_valid(self, form):
        really_exit = form.cleaned_data['really_exit']
        log.logger.debug('view really_exit %r', really_exit)

        if really_exit == 'yes':  # FIXME use bool via coerce?
            self.game.del_player(self.player_name)
            self.game.save()
        return super(GameExitView, self).form_valid(form)


class GameJoinView(GameViewMixin, FormView):
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
        self.game = self.get_game(kwargs['pk'])

        self.player_name = self.get_player_name()

        if self.player_name:
            player_image_url = avatar_url(self.player_name)
            if self.player_name not in self.game.gamedata['players']:
                self.game.add_player(self.player_name, player_image_url=player_image_url)
                if len(self.game.gamedata['players']) == 1:
                    self.game.start_new_round(winner_id=self.player_name)
                self.game.save()

            log.logger.debug('about to return reverse')
            return redirect(reverse('game-view', kwargs={'pk': self.game.id}))

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
