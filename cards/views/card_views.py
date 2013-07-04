from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.core.urlresolvers import reverse
from django.views.generic import (
    CreateView,
)

from cards.models import (
    SubmittedCard,
)

from cards.forms.card_forms import SubmittedCardForm


class SubmitCardView(CreateView):
    model = SubmittedCard
    form_class = SubmittedCardForm
    template_name = "submit_card.html"

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        self.user = request.user
        return super(SubmitCardView, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(SubmitCardView, self).get_form_kwargs()
        kwargs['user'] = self.user
        return kwargs

    def get_success_url(self):
        return reverse("submit-card")

    def get_context_data(self, **kwargs):
        context = super(SubmitCardView, self).get_context_data(**kwargs)
        context['action'] = reverse("submit-card")
        return context
