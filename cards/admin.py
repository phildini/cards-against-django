
from django.db import models
from django.contrib import admin

from cards.models import (
    Game,
    WhiteCard,
    BlackCard,
)

# Explicit > implicit.
admin.site.register(Game)
admin.site.register(WhiteCard)
admin.site.register(BlackCard)
