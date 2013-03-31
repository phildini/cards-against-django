# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#

from django import forms
from django.forms.widgets import RadioSelect, CheckboxSelectMultiple,Select
from django.core.exceptions import ValidationError
import random


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
            else: answers.append(self.cleaned_data.get(field_name))

        self.cleaned_data['card_selection'] = answers
        return self.cleaned_data

class CzarForm(forms.Form):

    def __init__(self, *args, **kwargs):
        cards = kwargs.pop('cards', ())
        super(CzarForm, self).__init__(*args, **kwargs)
        self.fields['card_selection'] = forms.ChoiceField(
            widget=RadioSelect,
            required = True,
            choices = cards,
        )



class GameForm(forms.Form):

    new_game = forms.CharField(max_length=140, required=False)
    player_name = forms.CharField(max_length=100)

    def __init__(self, *args, **kwargs):
        try:
            self.game_list = kwargs.pop('game_list')
        except KeyError:
            self.game_list = []
        super(GameForm, self).__init__(*args, **kwargs)
        self.fields["player_name"].initial = random.choice(['phil', 'chris', 'nicholle'])  # DEBUG
        if self.game_list:
            self.fields["new_game"].initial = None
            self.fields['game_list'] = forms.ChoiceField(
                    widget=RadioSelect,
                    required=False,
                    choices=self.game_list,
            )
        else:
            self.fields["new_game"].initial = random.choice(['cat', 'dog', 'bird'])  # DEBUG

    def clean(self):
        if self.cleaned_data.get('new_game') and self.cleaned_data.get('game_list'):
            raise ValidationError("You can't create a new game and join an existing one. Them's the rules.")
        if self.cleaned_data.get('new_game') in self.game_list:
            raise ValidationError("You can't creat a game with the same name as an existing one. Them's the rules.")
        return self.cleaned_data
