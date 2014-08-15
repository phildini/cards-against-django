from django.core.management.base import BaseCommand
from cards.models import Game

class Command(BaseCommand):

    def handle(self, *args, **options):
        game_list = Game.objects.filter(is_active=True)

        for game in game_list:
            game.deactivate_old_game()
