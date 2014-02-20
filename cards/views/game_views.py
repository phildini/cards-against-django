# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#

import json
import urllib

import redis

from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse
from django.utils.safestring import mark_safe
from django.utils.html import strip_tags
from django.views.generic import FormView, TemplateView
from django.views.generic.base import View
from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.conf import settings

from cards.forms.game_forms import (
    PlayerForm,
    LobbyForm,
    JoinForm,
    ExitForm,
)

from cards.models import (
    BlackCard,
    WhiteCard,
    Game,
    BLANK_MARKER,
    GAMESTATE_SUBMISSION,
    GAMESTATE_SELECTION,
    avatar_url,
    StandardSubmission,
    DEFAULT_HAND_SIZE,
)

import cards.log as log

TWITTER_SUBMISSION_LENGTH = 93

def push_notification(message='hello'):

    pool = redis.ConnectionPool(
        host=settings.REDIS_URL.hostname,
        port=settings.REDIS_URL.port,
        password=settings.REDIS_URL.password,
    )
    r = redis.Redis(connection_pool=pool)
    r.publish('games', message)
    pool.disconnect()


class GameViewMixin(object):

    def get_game(self, game_id):
        """Returns a game object for a given id.

        Raises Http404 if the game does not exist.

        """

        if not hasattr(self, '_games'):
            self._games = {}

        if game_id not in self._games:
            try:
                self._games[game_id] = Game.objects.get(pk=game_id)
            except Game.DoesNotExist:
                raise Http404

        expected_password = self._games[game_id].gamedata.get('password')
        if expected_password:
            session_details = self.request.session.get('session_details', {})
            session_password = self.request.GET.get('password')
            if session_password:
                session_details['password'] = session_password
                self.request.session['session_details'] = session_details
            session_password = session_details.get('password')
            if expected_password != session_password:
                # TODO show a form
                raise PermissionDenied()

        return self._games[game_id]

    def get_player_name(self, check_game_status=True):
        player_name = None

        if self.request.user.is_authenticated():
            player_name = self.request.user.username

        session_details = self.request.session.get('session_details')

        if not player_name:
            # Assume AnonymousUser
            if session_details:
                player_name = session_details.get('name')
            else:
                player_name = None  # observer

        # HOLY HELL THIS IS UGLY
        # But it fixes a bug.
        if player_name and session_details:
            if player_name != session_details.get('name'):
                if self.game.gamedata['players'].get(session_details.get('name')):
                    self.game.gamedata['players'][player_name] = self.game.gamedata['players'][session_details.get('name')]
                    self.game.del_player(session_details.get('name'))
                    if self.game.gamedata['card_czar'] == session_details.get('name'):
                        self.game.gamedata['card_czar'] = player_name

        # XXX check_game_status shouldn't be necessary, refactor it out
        # somehow!
        if (
            check_game_status and
            player_name and
            player_name not in self.game.gamedata['players']
        ):
            player_name = None

        return player_name


class LobbyView(FormView):

    template_name = 'lobby.html'
    form_class = LobbyForm

    def dispatch(self, *args, **kwargs):
        game_list = Game.objects.filter(is_active=True)

        for game in game_list:
            game.deactivate_old_game()
        if not self.request.user.is_staff:
            game_list = game_list.exclude(name__startswith='Private')

        self.game_list = game_list.values_list('id', 'name')

        return super(LobbyView, self).dispatch(*args, **kwargs)

    def get_success_url(self):
        return reverse('game-join-view', kwargs={'pk': self.game.id})

    def get_context_data(self, *args, **kwargs):
        context = super(LobbyView, self).get_context_data(*args, **kwargs)
        context['joinable_game_list'] = self.game_list  # TODO rename?

        return context

    def get_form_kwargs(self):
        kwargs = super(LobbyView, self).get_form_kwargs()
        if self.game_list:
            kwargs['game_list'] = [name for _, name in self.game_list]
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        session_details = self.request.session.get(
            'session_details', {})  # FIXME
        # FIXME if not a dict, make it a dict (upgrade old content)
        log.logger.debug('session_details %r', session_details)

        existing_game = True
        # Set the game properties in the database and session
        game_name = form.cleaned_data['game_name']
        if game_name:
            # Attempting to create a new game
            try:
                # see if already exists
                existing_game = Game.objects.get(name=game_name)
            except Game.DoesNotExist:
                existing_game = None

            if not existing_game:
                # really a new game
                tmp_game = Game(name=form.cleaned_data['game_name'])
                # XXX: We should feature-flag this code when we get feature flags working.
                if self.request.user.is_staff:
                    initial_hand_size = form.cleaned_data['initial_hand_size']
                    card_set = form.cleaned_data['card_set']
                    password = form.cleaned_data['password'] or None
                else:
                    card_set = []
                    initial_hand_size = DEFAULT_HAND_SIZE
                    password = None
                if not card_set:
                    # Are not staff or are staff and didn't select cardset(s)
                    # Either way they get default
                    card_set = ['v1.0', 'v1.2', 'v1.3', 'v1.4']
                tmp_game.gamedata = tmp_game.create_game(card_set, initial_hand_size=initial_hand_size, password=password)
                tmp_game.save()
                if password:
                    session_details['password'] = password
                self.game = tmp_game

        if existing_game:
            if not game_name:
                game_name = form.cleaned_data.get('game_list')

            existing_game = Game.objects.get(
                name=game_name)  # existing_game maybe a bool

            log.logger.debug('existing_game.gamedata %r',
                (existing_game.gamedata,)
            )
            log.logger.debug('existing_game.gamedata players %r',
                (existing_game.gamedata['players'],)
            )

            existing_game.save()

        # Set the player session details
        session_details['game'] = game_name
        self.request.session[
            'session_details'] = session_details  # this is probably kinda dumb.... Previously we used seperate session items for game and user name and that maybe what we need to go back to

        return super(LobbyView, self).form_valid(form)


def gen_qr_url(url, image_size=547):
    """Construct QR generator google URL with max size, from:

    https://chart.googleapis.com/chart? - All infographic URLs start with this root URL, followed by one or more parameter/value pairs. The required and optional parameters are specific to each image; read your image documentation.
        chs - Size of the image in pixels, in the format <width>x<height>
        cht - Type of image: 'qr' means QR code.
        chl - The data to encode. Must be URL-encoded.

    See https://google-developers.appspot.com/chart/infographics/docs/overview
    """
    url = urllib.quote(url)
    image_size_str = '%dx%d' % (image_size, image_size)
    result = 'https://chart.googleapis.com/chart?cht=qr&chs=%s&chl=%s' % (image_size_str, url)
    return result


class GameView(GameViewMixin, FormView):

    template_name = 'game_view.html'
    form_class = PlayerForm

    def dispatch(self, request, *args, **kwargs):
        log.logger.debug('%r %r', args, kwargs)
        self.game = self.get_game(kwargs['pk'])

        self.game.deactivate_old_game()

        if not self.game.can_be_played():
            return redirect(reverse('lobby-view'))

        self.player_name = self.get_player_name()
        session_details = self.request.session.get('session_details')

        card_czar_name = self.game.gamedata['card_czar']
        self.is_card_czar = self.player_name == card_czar_name

        return super(GameView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super(GameView, self).get_context_data(*args, **kwargs)

        log.logger.debug('game %r', self.game.gamedata['players'])
        black_card = BlackCard.objects.get(
            id=self.game.gamedata['current_black_card'],
        )

        context['tintg_server'] = settings.TINTG_SERVER
        context['show_form'] = self.can_show_form()
        context['game'] = self.game
        context['black_card'] = black_card.display_text()

        card_czar_name = self.game.gamedata['card_czar']
        context['card_czar_name'] = card_czar_name
        context['card_czar_avatar'] = self.game.gamedata[
            'players'][card_czar_name]['player_avatar']
        context['room_name'] = self.game.name
        if self.game.gamedata['submissions']:
            context['waiting_on'] = [
                name for name in self.game.gamedata['players'] if name not in self.game.gamedata['submissions'] and name != card_czar_name
            ]

        context['socketio'] = settings.SOCKETIO_URL
        context['qr_code_url'] = reverse('game-qrcode-view', kwargs={'pk': self.game.id})

        submissions = StandardSubmission.objects.filter(game=self.game).order_by('-id')[:10]
        context['submissions'] = [
            submission.export_for_display() for submission in submissions
        ]

        if self.player_name:
            if self.game.gamedata['submissions'] and not self.is_card_czar:
                player_submission = self.game.gamedata[
                    'submissions'].get(self.player_name)
                if player_submission:
                    submission = black_card.replace_blanks(
                        player_submission
                    )
                    context['filled_in_question'] = submission
                    twitter_submission = strip_tags(submission)
                    if len(twitter_submission) > TWITTER_SUBMISSION_LENGTH:
                        context['twitter_submission'] = twitter_submission[:TWITTER_SUBMISSION_LENGTH] + '...'
                    else:
                        context['twitter_submission'] = twitter_submission

        # at this point if player_name is None, they are an observer
        # otherwise a (supposedly) active player

        context['is_card_czar'] = self.is_card_czar
        context['player_name'] = self.player_name
        if self.player_name:
            context['player_avatar'] = self.game.gamedata[
                'players'][self.player_name]['player_avatar']

        return context

    def get_success_url(self):
        return reverse('game-view', kwargs={'pk': self.game.id})

    def form_valid(self, form):
        if self.is_card_czar:
            winner = form.cleaned_data['card_selection']
            log.logger.debug(winner)
            winner = winner[0]  # for some reason we have a list
            winner_name = winner 

            # NOTE StandardSubmission could benefit from a round number to ensure unique key, this would remove the need for the [0] offset/slice
            winning_submission = StandardSubmission.objects.filter(
                game=self.game,
                blackcard=self.game.gamedata['current_black_card'],
                submissions__in=self.game.gamedata['submissions'][winner]  # TODO equality instead of in?; submissions=self.game.gamedata['submissions'][winner][0]
            )[0]
            winning_submission.winner = True
            winning_submission.save()
            self.game.start_new_round(self.player_name, winner_name, winner)
        else:
            submitted = form.cleaned_data['card_selection']
            # The form returns unicode strings. We want ints in our list.
            white_card_list = [int(card) for card in submitted]
            self.game.submit_white_cards(
                self.player_name, white_card_list)  # FIXME catch GameError and/or check before hand

            if self.game.gamedata['filled_in_texts']:
                log.logger.debug(
                    'filled_in_texts %r',
                    self.game.gamedata['filled_in_texts']
                )
        self.game.save()

        push_notification(str(self.game.name))
        
        return super(GameView, self).form_valid(form)

    def get_form_kwargs(self):
        black_card_id = self.game.gamedata['current_black_card']
        kwargs = super(GameView, self).get_form_kwargs()
        if self.player_name and self.can_show_form():
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
                    (card_id, mark_safe(card_text.capitalize()))
                    for card_id, card_text
                    in WhiteCard.objects.filter(
                        id__in=self.game.gamedata[
                            'players'][self.player_name]['hand']
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
            mimetype='application/json'
        )


class GameExitView(GameViewMixin, FormView):
    template_name = 'game_exit.html'
    form_class = ExitForm

    def dispatch(self, request, *args, **kwargs):
        log.logger.debug('%r %r', args, kwargs)
        self.game = self.get_game(kwargs['pk'])

        this_user = self.get_player_name()
        self.player_name = this_user
        if request.user.is_staff:  # TODO or if player "owns" game
            # Only staff can kick other users
            #player_name = kwargs.get('player_name')  # FIXME setup url dispatcher
            player_name = request.GET.get('player_name')  # e.g. /game/24/exit?player_name=JohnSmith
            self.player_name = player_name or this_user

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
        context['exit_player_name'] = self.player_name
        return context

    def get_success_url(self):
        return reverse('game-view', kwargs={'pk': self.game.id})

    def form_valid(self, form):
        really_exit = form.cleaned_data['really_exit']
        log.logger.debug('view really_exit %r', really_exit)

        if really_exit == 'yes':  # FIXME use bool via coerce?
            self.game.del_player(self.player_name)
            self.game.save()
            push_notification(str(self.game.name))
        return super(GameExitView, self).form_valid(form)


class GameJoinView(GameViewMixin, FormView):

    """This is a temp function that expects a user already exists and is logged
    in, then joins them to an existing game.

    We want to support real user accounts but also anonymous, which is why
    this is a debug routine for now.

    TODO password protection check on join. Should this be part of GameViewMixin, a new game mixin, or GameView?
    TODO create a game (with no players, redirect to join game for game creator).

    """

    template_name = 'game_join.html'
    form_class = JoinForm

    def dispatch(self, request, *args, **kwargs):
        self.game = self.get_game(kwargs['pk'])

        # FIXME perform anon user name is not a registered username check
        # (same as in JoinForm) in case the session cookie was set BEFORE a
        # user was registered.
        self.player_name = self.get_player_name(check_game_status=False)

        if self.player_name:
            if request.user.is_authenticated():
                player_image_url = avatar_url(request.user.email)
            else:
                player_image_url = avatar_url(self.player_name)
            if self.player_name not in self.game.gamedata['players']:
                self.game.add_player(
                    self.player_name, player_image_url=player_image_url)
                if len(self.game.gamedata['players']) == 1:
                    self.game.start_new_round(winner_id=self.player_name)
                self.game.save()

            log.logger.debug('about to return reverse')
            return redirect(reverse('game-view', kwargs={'pk': self.game.id}))

        return super(GameJoinView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super(GameJoinView, self).get_context_data(*args, **kwargs)
        context['show_form'] = True
        # if we are here we need a player name (or they need to log in so we can get a player name)
        # TODO and maybe a password

        return context

    def get_success_url(self):
        return reverse('game-join-view', kwargs={'pk': self.game.id})

    def form_valid(self, form):
        player_name = form.cleaned_data['player_name']
        session_details = {}
        session_details['name'] = player_name
        self.request.session['session_details'] = session_details
        return super(GameJoinView, self).form_valid(form)


class GameQRCodeView(GameViewMixin, TemplateView):

    """Display a page with a QR code for quick/easy game joining
    """

    template_name = 'game_qr.html'

    def get_context_data(self, *args, **kwargs):
        context = super(GameQRCodeView, self).get_context_data(*args, **kwargs)

        self.game = self.get_game(kwargs['pk'])  # is this the right place for this?

        context['testy'] = 'pants'
        tmp_pass = self.game.gamedata.get('password')
        game_url = reverse('game-view', kwargs={'pk': self.game.id})
        game_url = self.request.build_absolute_uri(game_url)
        if tmp_pass:
            game_url = game_url + '?password=%s' % tmp_pass  # possible html escape issue?
        context['game_url'] = game_url
        context['qr_code_url'] = gen_qr_url(game_url)

        return context
