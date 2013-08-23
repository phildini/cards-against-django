from cards.models import Game
from cards.api.serializers import GameSerializer
from rest_framework import mixins
from rest_framework import generics

class GameDetail(generics.RetrieveAPIView):
    queryset = Game.objects.all()
    serializer_class = GameSerializer