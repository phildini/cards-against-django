from django.conf.urls import patterns, include, url

from views.game_views import (
    GameView,
    LobbyView,
    GameJoinView,
    GameExitView,
    GameQRCodeView,
)
from cards.api.views import GameDetail

urlpatterns = patterns('',
    url(r'^(?P<pk>\d+)/$',
       GameView.as_view(), name='game-view'),
    url(r'^(?P<pk>\d+)/join$',
       GameJoinView.as_view(), name='game-join-view'),
    url(r'^(?P<pk>\d+)/exit$',
       GameExitView.as_view(), name='game-exit-view'),
    url(r'^(?P<pk>\d+)/qrcode$',
       GameQRCodeView.as_view(), name='game-qrcode-view'),
    # This will probably change.
    url(r'^(?P<pk>\d+)/api$',
        GameDetail.as_view(), name="game-detail"),
)
