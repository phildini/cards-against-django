# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#

from django.db import models

# Create your models here.

class Game(models.Model):

    name = models.CharField(max_length = 140)
    game_state = models.CharField(max_length = 140)
