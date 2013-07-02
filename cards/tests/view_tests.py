#!/usr/bin/env python
# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase
from cards.models import Game
from cards.views import avatar_url


class SimpleTest(TestCase):

    def test_basic_addition(self):
        """Tests that 1 + 1 always equals 2."""
        self.assertEqual(1 + 1, 2)


class LobbyViewTests(TestCase):
    def test_game_list(self):
        game_1 = Game.objects.create(name='Test')
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue('joinable_game_list' in resp.context)
        self.assertEqual(resp.context['joinable_game_list'][0][1], 'Test')

class GameViewTests(TestCase):
    def setUp(self):
        game = Game.objects.create(name="Test")
        game.gamedata = game.create_game()
        game.add_player('Philip', avatar_url('Philip'))
        game.save()
        self.game = game

