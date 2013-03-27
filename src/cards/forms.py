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
            required=True,
            widget=CheckboxSelectMultiple,
            choices=cards,
        )
        self.blanks = blanks

    def clean(self):
        if len(self.cleaned_data.get('card_selection')) > self.blanks:
            raise ValidationError("Hey now. No cheating. Only the right number of cards, please.")
        if len(self.cleaned_data.get('card_selection')) < self.blanks:
            raise ValidationError("Ruh-roh Shaggy. You need to choose more cards.")

        return self.cleaned_data
