# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#

import random
import hashlib
import urllib

from django.db import models
from django.contrib.auth.models import User

from jsonfield import JSONField
from model_utils.models import TimeStampedModel

import log


def gravatar_url(email, size=50, default='monsterid'):
    """Generate url for Gravatar image
    email - email address
    default = default_image_url or default hash type
    """
    gravatar_url = "http://www.gravatar.com/avatar/" + hashlib.md5(email.lower()).hexdigest() + "?"
    if default:
        gravatar_url += urllib.urlencode({'d': default, 's': str(size)})
    else:
        gravatar_url += urllib.urlencode({'s': str(size)})
    return gravatar_url

avatar_url = gravatar_url


class Game(TimeStampedModel):

    name = models.CharField(max_length=140, unique=True)  # could use pk, but we can use id.
    game_state = models.CharField(max_length=140)
    is_active = models.BooleanField(default=True)
    gamedata = JSONField()  # See view doc comments

    def __unicode__(self):
        # FIXME add game start time, include num players and rounds in display name
        return self.name

    def create_game(self):
        log.logger.debug("New Game called")
        """Create shuffled decks
        uses built in random, it may be better to plug-in a better
        random init routine and/also consider using
        https://pypi.python.org/pypi/shuffle/

        Also take a look at http://code.google.com/p/gcge/
        """
        shuffled_white = [x[0] for x in WhiteCard.objects.values_list('id')]
        random.shuffle(shuffled_white)
        shuffled_black = [x[0] for x in BlackCard.objects.values_list('id')]
        random.shuffle(shuffled_black)

        # Basic data object for a game. Eventually, this will be saved in cache.
        return {
            'players': {},
            'current_black_card': None,  # get a new one my shuffled_black.pop()
            'submissions': {},
            'round': 1,  # FIXME reset() which is next round should be called at start of each round, when that is done this should be zero
            'card_czar': '',
            'white_deck': shuffled_white,
            'black_deck': shuffled_black,
            'mode': 'submitting',
        }

    # FIXME should be using a player object
    def create_player(self, player_name):
        log.logger.debug("new player called")
        # Basic data obj for player. Eventually, this will be saved in cache.
        return {
            'hand': [],
            'wins': 0,
            'player_avatar': avatar_url(player_name),
        }


class Player(TimeStampedModel):

    # These are the fields I can think of for now, but we're not using it yet,
    # so we can adjust as needed.
    name = models.CharField(max_length=140)
    game = models.ForeignKey(Game)
    user = models.ForeignKey(
        User,
        blank=True,
        null=True,
        on_delete=models.SET_NULL
    )
    player_data = JSONField(blank=True)
    wins = models.IntegerField(blank=True)

    def __str__(self):
        return self.name


class BlackCard(models.Model):
    text = models.CharField(max_length=255)
    draw = models.SmallIntegerField(default=0)
    pick = models.SmallIntegerField(default=1)
    watermark = models.CharField(max_length=5, null=True)

    class Meta:
        db_table = 'black_cards'

    def __unicode__(self):
        return self.text


class WhiteCard(models.Model):
    text = models.CharField(max_length=255)
    watermark = models.CharField(max_length=5, null=True)

    class Meta:
        db_table = 'white_cards'

    def __unicode__(self):
        return self.text
