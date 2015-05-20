from django.forms import ModelForm

from django.contrib.auth.models import User

from cards.models import SubmittedCard


class SubmittedCardForm(ModelForm):
    class Meta:
        model = SubmittedCard
        fields = ['submitter', 'card_type', 'text']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super(SubmittedCardForm, self).__init__(*args, **kwargs)
        self.fields['submitter'].queryset = User.objects.filter(id=user.id)