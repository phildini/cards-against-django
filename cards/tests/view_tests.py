#!/usr/bin/env python
# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
from django.core.urlresolvers import reverse
from django.test.client import RequestFactory
from django.test import TestCase

from cards.views.game_views import (
    LobbyView,
    GameView,
)
from cards.models import (
    Game,
    avatar_url,
    GAMESTATE_SUBMISSION,
    GAMESTATE_SELECTION,
)
from cards import factories


class SimpleTest(TestCase):

    def test_basic_addition(self):
        """Tests that 1 + 1 always equals 2."""
        self.assertEqual(1 + 1, 2)


class LobbyViewTests(TestCase):

    def setUp(self):
        self.game = factories.GameFactory.create(
            name='Test',
            is_active=True
        )
        self.request_factory = RequestFactory()
        self.request = self.request_factory.get(reverse('lobby-view'))
        self.request.user = factories.UserFactory.create()

    def test_basic_response(self):
        response = LobbyView.as_view()(self.request)
        self.assertEqual(response.status_code, 200)

    def test_game_list(self):
        response = LobbyView.as_view()(self.request)
        self.assertTrue('joinable_game_list' in response.context_data)
        self.assertEqual(response.context_data['joinable_game_list'][0][1], 'Test')

    def test_private_game_not_shown(self):
        self.game.name = 'Private Test'
        self.game.save()
        response = LobbyView.as_view()(self.request)
        self.assertTrue('joinable_game_list' in response.context_data)
        self.assertEqual(list(response.context_data['joinable_game_list']), [])

    def test_inactive_game_not_shown(self):
        self.game.is_active = False
        self.game.save()
        response = LobbyView.as_view()(self.request)
        self.assertTrue('joinable_game_list' in response.context_data)
        self.assertEqual(list(response.context_data['joinable_game_list']), [])


class GameViewTests(TestCase):

    def setUp(self):
        self.game = factories.GameFactory.create(
            name='Test',
            is_active='True'
        )
        self.request_factory = RequestFactory()
        self.request = self.request_factory.get(
            reverse('game-view', args=(self.game.id,))
        )

    def test_get_game(self):
        game = GameView().get_game(self.game.id)
        self.assertEqual(game, self.game)

    def test_can_show_form_is_czar_selection_state(self):
        game_view = GameView()
        game_view.player_name = True
        game_view.is_card_czar = True
        self.game.game_state = GAMESTATE_SELECTION
        game_view.game = self.game
        self.assertTrue(game_view.can_show_form())

