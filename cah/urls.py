# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#

from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

from django.views.generic.base import RedirectView

from robots_txt.views import RobotsTextView

from cards.views.game_views import (
    LobbyView,
)

from cards.views.card_views import SubmitCardView, import_cards

# from cards.views.cards

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'cah.views.home', name='home'),
    # url(r'^cah/', include('cah.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    url(r'^robots.txt$', RobotsTextView.as_view()),
    url(r'^$', LobbyView.as_view(), name="lobby-view",),
    url(r'^game/', include('cards.urls')),
    url(r'^import', import_cards, name="import-cards"),
    url(r'^submit', SubmitCardView.as_view(), name="submit-card"),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^accounts/', include('allauth.urls')),
)
