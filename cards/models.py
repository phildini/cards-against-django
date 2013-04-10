# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#

from django.db import models

from jsonfield import JSONField


# Create your models here.

class Game(models.Model):

    name = models.CharField(max_length = 140)  # FIXME pk
    game_state = models.CharField(max_length = 140)
    
    gamedata = JSONField()

    def __unicode__(self):
        # FIXME add game start time, include num players and rounds in display name
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
