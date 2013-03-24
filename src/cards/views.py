# Create your views here.
from django.views.generic import TemplateView
from forms import PlayerForm

class PlayerView(TemplateView):

	template_name = 'player.html'

	def get_context_data(self, **kwargs):
		context = super(TemplateView, self).get_context_data(**kwargs)
		cards = {1:"one", 2:"two", 3:"three"}
		context['cards'] = cards
		form = PlayerForm(cards=cards)
		context['form'] = form
		return context


