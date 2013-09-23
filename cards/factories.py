import factory
from cards import models


class GameFactory(factory.django.DjangoModelFactory):
    FACTORY_FOR = models.Game

