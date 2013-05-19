from django.conf.urls.defaults import patterns, include, url

from views import (
    GameView,
    LobbyView,
    GameCheckReadyView,
    GameJoinView,
    GameExitView,
    debug_deactivate_old_games,
)

urlpatterns = patterns('',
    url(r'^(?P<pk>\d+)/$', GameView.as_view(), name="game-view"),
    url(r'^(?P<pk>\d+)/checkready$', GameCheckReadyView.as_view(), name="game-check-ready-view"),
    url(r'^(?P<pk>\d+)/join$', GameJoinView.as_view(), name="game-join-view"),
    url(r'^(?P<pk>\d+)/exit$', GameExitView.as_view(), name="game-exit-view"),
)
