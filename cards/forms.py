# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#

import random

from django import forms
from django.forms.widgets import (
    RadioSelect,
)
from django.core.exceptions import ValidationError
from django.core.cache import cache  # this maybe a bad idea

from cards.models import Game


class PlayerForm(forms.Form):

    def __init__(self, *args, **kwargs):
        cards = kwargs.pop('cards', ())
        blanks = kwargs.pop('blanks', 1)
        super(PlayerForm, self).__init__(*args, **kwargs)
        for blank in xrange(blanks):
            self.fields['card_selection%d' % (blank,)] = forms.ChoiceField(
                widget=RadioSelect,
                required=True,
                choices=cards,
            )
        self.blanks = blanks

    def clean(self):
        answers = []
        for blank in xrange(self.blanks):
            field_name = 'card_selection%d' % (blank,)
            if self.cleaned_data.get(field_name) in answers:
                raise ValidationError("You can't use the same answer twice")
            else:
                answers.append(self.cleaned_data.get(field_name))

        self.cleaned_data['card_selection'] = answers
        return self.cleaned_data


class CzarForm(forms.Form):

    def __init__(self, *args, **kwargs):
        cards = kwargs.pop('cards', ())
        super(CzarForm, self).__init__(*args, **kwargs)
        self.fields['card_selection'] = forms.ChoiceField(
            widget=RadioSelect,
            required=True,
            choices=cards,
        )


class LobbyForm(forms.Form):
    """
    The form for creating or joining a game from the lobby view
    """

    new_game = forms.CharField(max_length=140, required=False)
    player_name = forms.CharField(max_length=100)

    def __init__(self, *args, **kwargs):
        try:
            self.game_list = kwargs.pop('game_list')
        except KeyError:
            self.game_list = []
        player_name = kwargs.pop('player_name')
        super(LobbyForm, self).__init__(*args, **kwargs)
        self.fields["player_name"].initial = player_name
        if self.game_list:
            self.fields["new_game"].initial = None
        else:
            self.fields["new_game"].initial = random.choice(['cat', 'dog', 'bird'])  # DEBUG

    def clean(self):
        new_game = self.cleaned_data.get('new_game')
        if not new_game:
            raise ValidationError("Create a game needs a non empty name.")
        if new_game in self.game_list:
            raise ValidationError("You can't create a game with the same name as an existing one. Them's the rules.")
        return self.cleaned_data


class JoinForm(forms.Form):
    """The form for setting user name when joining a game
    TODO password field..
    """

    player_name = forms.CharField(max_length=100)

    def __init__(self, *args, **kwargs):
        super(JoinForm, self).__init__(*args, **kwargs)
        player_counter = cache.get('player_counter', 0) + 1
        cache.set('player_counter', player_counter)
        self.fields["player_name"].initial = 'Auto Player %d' % player_counter

    def clean(self):
        player_name = self.cleaned_data.get('player_name')
        if not player_name:
            raise ValidationError("Player needs a non empty name.")
        # TODO check to make sure we don't have a dupe username in the game
        return self.cleaned_data
