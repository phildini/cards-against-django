# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#

from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

from cards.views import (
    GameView,
    LobbyView,
    GameJoinView,
    GameExitView,
    debug_deactivate_old_games,
)

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'cah.views.home', name='home'),
    # url(r'^cah/', include('cah.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^$', LobbyView.as_view(), name="lobby-view",),
    url(r'^game/', include('cards.urls')),
    url(r'^super_secret_thing$', debug_deactivate_old_games),
    url(r'^admin/', include(admin.site.urls)),
)
