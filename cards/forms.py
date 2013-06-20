# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#

import random

from django.contrib.auth.models import User
from django.db.models import Q

from django import forms
from django.forms.widgets import (
    RadioSelect,
)
from django.core.exceptions import ValidationError
from django.core.cache import cache  # this maybe a bad idea

from models import CardSet
import log


class PlayerForm(forms.Form):

    def __init__(self, *args, **kwargs):
        cards = kwargs.pop('cards', ())
        self.blanks = kwargs.pop('blanks', 1)

        super(PlayerForm, self).__init__(*args, **kwargs)

        for blank in xrange(self.blanks):
            self.fields['card_selection%d' % (blank,)] = forms.ChoiceField(
                widget=RadioSelect,
                required=True,
                choices=cards,
            )

    def clean(self):
        answers = []
        for blank in xrange(self.blanks):
            field_name = 'card_selection%d' % (blank,)
            single_answer = self.cleaned_data.get(field_name)
            if single_answer in answers:
                raise ValidationError("You can't use the same answer twice")
            else:
                log.logger.debug(
                    'player submit white card; %s, %r', field_name, single_answer)
                answers.append(single_answer)

        log.logger.debug('player submit answers; %r', answers)
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

    """The form for creating or joining a game from the lobby view."""

    new_game = forms.CharField(
        max_length=140,
        label="Create a new game or join one below",
        required=True
    )
    # XXX: We should feature-flag this code when we get feature flags working.
    # card_set = forms.ModelMultipleChoiceField(
    #     queryset=CardSet.objects.all().order_by('-name')
    # )

    def __init__(self, *args, **kwargs):
        self.game_list = kwargs.pop('game_list', [])

        super(LobbyForm, self).__init__(*args, **kwargs)

        if self.game_list:
            self.fields['new_game'].initial = None
        else:
            self.fields['new_game'].initial = random.choice(
                ['cat', 'dog', 'bird']
            )  # DEBUG

    def clean_new_game(self):
        new_game = self.cleaned_data.get('new_game')

        if new_game in self.game_list:
            raise ValidationError(
                "You can't create a game with the same name as "
                "an existing one. Them's the rules."
            )
        # card_set = self.cleaned_data.get('card_set')  # check for non-empty
        # cardsets?

        return new_game


class JoinForm(forms.Form):

    """The form for setting user name when joining a game.

    TODO password field..

    """

    player_name = forms.CharField(
        max_length=100,
        required=True,
    )

    def __init__(self, *args, **kwargs):
        super(JoinForm, self).__init__(*args, **kwargs)

        player_counter = cache.get('player_counter', 0) + 1
        cache.set('player_counter', player_counter)
        self.fields['player_name'].initial = 'Auto Player %d' % player_counter

    def clean_player_name(self):
        # check to make sure we don't have an existing registered username/email
        player_name = self.cleaned_data.get('player_name')
        existing_users = User.objects.filter(
                Q(username__iexact=player_name) | Q(email__iexact=player_name)
            ).values_list('id')
        if existing_users:
            raise ValidationError(
                "There is aleady a registered user with that name. "
                "Enter a different username."
            )

        return player_name


class ExitForm(forms.Form):
    really_exit = forms.ChoiceField(
        widget=RadioSelect,
        required=True,
        choices=[('yes', 'yes'), ('no', 'no')],
    )
