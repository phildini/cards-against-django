from django import forms
from django.forms.widgets import RadioSelect

class PlayerForm(forms.Form):

	def __init__(self, *args, **kwargs):
		cards = kwargs.pop('cards', ())
		super(PlayerForm, self).__init__(*args, **kwargs)
		self.fields['card_selection'] = forms.ChoiceField(required=True, widget=RadioSelect, choices=cards)

		
