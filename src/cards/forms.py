from django import forms
from django.forms.widgets import RadioSelect

CARDS = ((1, 'A bloody pacifier.'), (2, 'A Bop It.'), (3, 'Clearing a bloody path through Walmart with a scimitar.'))

class PlayerForm(forms.Form):
	card_selection = forms.MultipleChoiceField(required=True, widget=RadioSelect, choices=CARDS)

	def __init__(self, *args, **kwargs):
		cards = kwargs.pop('cards')

		super(forms.Form, self).__init__(*args, **kwargs)
		self.card_selection = forms.MultipleChoiceField(required=True, widget=RadioSelect, choices=cards)
