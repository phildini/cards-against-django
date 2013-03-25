# Create your views here.
import json
import os
from django.conf import settings
from django.views.generic import FormView, TemplateView
from django.core.urlresolvers import reverse
from forms import PlayerForm

class PlayerView(FormView):

	template_name = 'player.html'
	form_class = PlayerForm

	def __init__(self, *args, **kwargs):
		self.read_player()
		super(PlayerView, self).__init__(*args, **kwargs)


	def get_success_url(self):
		return reverse('player-view')

	def get_context_data(self, **kwargs):
		context = super(PlayerView, self).get_context_data(**kwargs)
		self.request.session['player_name'] = self.player['name']
		context['name_from_session'] = self.request.session.get('player_name', '')
		self.is_card_czar = context['is_card_czar'] = self.player['is_card_czar'] == 1
		context['cards'] = self.player['hand']
		context['player_name'] = self.player['name']
		context['selected'] = self.player['selected']
		return context

	def get_form_kwargs(self):
		kwargs = super(PlayerView, self).get_form_kwargs()
		kwargs['cards'] = tuple(tuple(card) for card in self.player['hand'])
		return kwargs

	def form_valid(self, form):
		self.player['selected'] = form.cleaned_data['card_selection']
		self.write_player()
		print form.cleaned_data['card_selection']
		return super(PlayerView, self).form_valid(form)

	def read_player(self):
		with open(os.path.join(settings.PROJECT_ROOT, 'player.json')) as data:
			self.player = json.loads(data.read())

	def write_player(self):
		with open(os.path.join(settings.PROJECT_ROOT, 'player.json'), 'w') as data:
			data.write(json.dumps(self.player))

class GameView(FormView):

	template_name = 'player.html'
	form_class = PlayerForm

	# def get_form_kwargs


class LobbyView(TemplateView):

	template_name = 'lobby.html'