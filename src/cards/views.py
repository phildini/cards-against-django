# Create your views here.
from django.views.generic import FormView
from forms import PlayerForm

class PlayerView(FormView):

	template_name = 'player.html'
	selection = ''
	cards = ((1, 'A bloody pacifier.'), (2, 'A Bop It.'), (3, 'Clearing a bloody path through Walmart with a scimitar.'))
	form_class = PlayerForm


	def get_success_url(self):
		return '/admin'

	def get_context_data(self, **kwargs):
		context = super(FormView, self).get_context_data(**kwargs)
		context['cards'] = self.cards
		if self.selection:
			context['select_card'] = self.selection
		return context

	def get_form_kwargs(self):
		kwargs = super(FormView, self).get_form_kwargs()
		kwargs['cards'] = self.cards
		return kwargs