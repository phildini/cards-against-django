# Create your views here.
import json
import os
from django.conf import settings
from django.views.generic import FormView
from forms import PlayerForm

class PlayerView(FormView):

	template_name = 'player.html'
	form_class = PlayerForm

	def __init__(self, *args, **kwargs):
		self.read_player()
		super(PlayerView, self).__init__(*args, **kwargs)


	def get_success_url(self):
		return '/'

	def get_context_data(self, **kwargs):
		context = super(PlayerView, self).get_context_data(**kwargs)
		context['cards'] = self.player['1']['hand']
		context['player_name'] = self.player['1']['name']
		context['selected'] = self.player['1']['selected']
		return context

	def get_form_kwargs(self):
		kwargs = super(PlayerView, self).get_form_kwargs()
		kwargs['cards'] = tuple(tuple(card) for card in self.player['1']['hand'])
		return kwargs

	def form_valid(self, form):
		self.selection = form.cleaned_data['card_selection']
		print form.cleaned_data['card_selection']
		return super(PlayerView, self).form_valid(form)

	def read_player(self):
		with open(os.path.join(settings.PROJECT_ROOT, 'player.json')) as data:
			self.player = json.loads(data.read())