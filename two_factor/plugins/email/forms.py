from django import forms
from django.utils.translation import gettext_lazy as _


class EmailForm(forms.Form):
    email = forms.EmailField(label=_("Email address"))

    def __init__(self, **kwargs):
        kwargs.pop('device', None)
        super().__init__(**kwargs)
