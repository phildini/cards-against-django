# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#

from django import forms
from django.forms.widgets import RadioSelect, CheckboxSelectMultiple
from django.core.exceptions import ValidationError


class PlayerForm(forms.Form):

    def __init__(self, *args, **kwargs):
        cards = kwargs.pop('cards', ())
        blanks = kwargs.pop('blanks', 1)
        super(PlayerForm, self).__init__(*args, **kwargs)
        self.fields['card_selection'] = forms.MultipleChoiceField(
            widget=CheckboxSelectMultiple,
            required=True,
            choices=cards,
        )
        self.blanks = blanks

    def clean(self):
    	if self.cleaned_data.get('card_selection'):
	        if len(self.cleaned_data.get('card_selection')) > self.blanks:
	            raise ValidationError("Hey now. No cheating. Only the right number of cards, please.")
	        if len(self.cleaned_data.get('card_selection')) < self.blanks:
	            raise ValidationError("Ruh-roh Shaggy. You need to choose more cards.")

        return self.cleaned_data


class GameForm(forms.Form):

	new_game = forms.CharField(max_length=140, required=False)
	player_name = forms.CharField(max_length=100)

	def __init__(self, *args, **kwargs):
		try:
			self.game_list = kwargs.pop('game_list')
		except KeyError:
			self.game_list = []
		super(GameForm, self).__init__(*args, **kwargs)
		if self.game_list:
			self.fields['game_list'] = forms.ChoiceField(
				widget=RadioSelect,
				required=False,
				choices=game_list,
			)

	def clean(self):
		if self.cleaned_data.get('new_game') and self.cleaned_data.get('game_list'):
			raise ValidationError("You can't create a new game and join an existing one. Them's the rules.")
		if self.cleaned_data.get('new_game') in self.game_list:
			raise ValidationError("You can't creat a game with the same name as an existing one. Them's the rules.")
		return self.cleaned_data
