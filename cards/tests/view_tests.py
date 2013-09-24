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

from cards.views.game_views import LobbyView
from cards.models import (
    Game,
    avatar_url,
)
from cards import factories


class SimpleTest(TestCase):

    def test_basic_addition(self):
        """Tests that 1 + 1 always equals 2."""
        self.assertEqual(1 + 1, 2)


class LobbyViewTests(TestCase):

    def setUp(self):
        self.game = factories.GameFactory.create(name='Test', is_active=True)
        self.request_factory = RequestFactory()
        self.request = self.request_factory.get(reverse('lobby-view'))

    def test_basic_response(self):
        response = LobbyView.as_view()(self.request)
        self.assertEqual(response.status_code, 200)

    def test_game_list(self):
        request = self.request_factory.get(reverse('lobby-view'))
        response = LobbyView.as_view()(request)
        self.assertTrue('joinable_game_list' in response.context_data)
        self.assertEqual(response.context_data['joinable_game_list'][0][1], 'Test')

    def test_private_game_not_shown(self):
        self.game.name = 'Private Test'
        self.game.save()
        request = self.request_factory.get(reverse('lobby-view'))
        response = LobbyView.as_view()(request)
        self.assertTrue('joinable_game_list' in response.context_data)
        self.assertEqual(list(response.context_data['joinable_game_list']), [])

    def test_inactive_game_not_shown(self):
        self.game.is_active = False
        self.game.save()
        request = self.request_factory.get(reverse('lobby-view'))
        response = LobbyView.as_view()(request)
        self.assertTrue('joinable_game_list' in response.context_data)
        self.assertEqual(list(response.context_data['joinable_game_list']), [])
