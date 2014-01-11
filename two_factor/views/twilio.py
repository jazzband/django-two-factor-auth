from django.conf import settings
from django.contrib.sites.models import get_current_site
from django.http import HttpResponse
from django.utils import translation
from django.utils.translation import (ugettext_lazy as _, pgettext,
                                      check_for_language)
from django.views.decorators.cache import never_cache
from django.views.generic import View

from ..gateways.twilio import validate_voice_locale
from .utils import class_view_decorator


@class_view_decorator(never_cache)
class TwilioCallApp(View):
    """
    View used by Twilio for the interactive token verification by phone.
    """
    template = '<?xml version="1.0" encoding="UTF-8" ?>' \
               '<Response><Say language="%(locale)s">' \
               '%(prompt)s</Say></Response>'

    # Translators: should be a language supported by Twilio,
    # see http://bit.ly/187I5cr
    prompt = _('Hi, this is %(site_name)s calling. Please enter the '
               'following code on your screen: %(token)s. Repeat: '
               '%(token)s.')

    def get(self, request, token):
        locale = request.GET.get('locale', '')
        if not check_for_language(locale):
            locale = settings.LANGUAGE_CODE
        validate_voice_locale(locale)
        with translation.override(locale):
            # Build the prompt. The numbers have to be clearly pronounced,
            # this is by creating a string like "1. 2. 3. 4. 5. 6.", this way
            # Twilio reads the numbers one by one.
            prompt = self.prompt % {
                'token': '. '.join(token),
                'site_name': get_current_site(request).name,
            }
            prompt = self.template % {
                # Translators: twilio_locale should be a locale supported by
                # Twilio, see http://bit.ly/187I5cr
                'locale': pgettext('twilio_locale', 'en'),
                'prompt': prompt,
            }
            return HttpResponse(prompt, 'text/xml')
