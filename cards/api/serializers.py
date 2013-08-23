from rest_framework import serializers
from cards.models import Game

class GameSerializer(serializers.Serializer):
    pk = serializers.Field()
    name = serializers.CharField(max_length=140)
    game_state = serializers.CharField(max_length=140)
    is_active = serializers.BooleanField()
    gamedata = serializers.Field()
