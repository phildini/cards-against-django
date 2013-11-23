import factory
from django.contrib.auth.models import User
from cards import models


class GameFactory(factory.django.DjangoModelFactory):
    FACTORY_FOR = models.Game


class UserFactory(factory.django.DjangoModelFactory):
    FACTORY_FOR = User

