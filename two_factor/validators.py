from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from phonenumber_field.phonenumber import to_python


# See upstream patch can be removed once merged.
# https://github.com/stefanfoulis/django-phonenumber-field/pull/81
def validate_international_phonenumber(value):
    phone_number = to_python(value)
    if phone_number and not phone_number.is_valid():
        raise ValidationError(_('The phone number entered is not valid.'), code='invalid')
