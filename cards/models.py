# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#

from django.db import models
from django.contrib.auth.models import User

from jsonfield import JSONField
from model_utils.models import TimeStampedModel

# Create your models here.

class Game(TimeStampedModel):

    name = models.CharField(max_length=140, unique=True)  # could use pk, but we can use id.
    game_state = models.CharField(max_length=140)
    is_active = models.BooleanField(default=True)
    gamedata = JSONField()  # See view doc comments

    def __unicode__(self):
        # FIXME add game start time, include num players and rounds in display name
        return self.name


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
