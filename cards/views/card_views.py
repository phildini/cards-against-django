import json

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.core.urlresolvers import reverse
from django.views.generic import (
    CreateView,
)

from cards.models import (
    SubmittedCard,
    dict2db,
)

from cards.forms.card_forms import SubmittedCardForm

load_json = json.loads


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


@staff_member_required
def import_cards(request):
    raw_json_str = ''
    raw_json_str = request.GET.get('json')
    if raw_json_str is None:
        return HttpResponse('Looks like we need a form')
    try:
        d = load_json(raw_json_str)
    except ValueError, info:
        return HttpResponse(repr(info))
    verbosity = 0
    replace_existing = False
    results = dict2db(d, verbosity, replace_existing)
    return HttpResponse(repr(results))
