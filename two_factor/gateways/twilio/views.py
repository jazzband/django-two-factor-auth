from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.http import HttpResponse
from django.utils import translation
from django.utils.translation import (
    check_for_language, gettext_lazy as _, pgettext,
)
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

from ...views.utils import class_view_decorator
from .gateway import validate_voice_locale


@class_view_decorator(never_cache)
@class_view_decorator(csrf_exempt)
class TwilioCallApp(View):
    """
    View used by Twilio for the interactive token verification by phone.
    """
    templates = {
        'press_a_key': '<?xml version="1.0" encoding="UTF-8" ?>'
                       '<Response>'
                       '  <Gather timeout="15" numDigits="1" finishOnKey="">'
                       '    <Say language="%(locale)s">%(press_a_key)s</Say>'
                       '  </Gather>'
                       '  <Say language="%(locale)s">%(no_input)s</Say>'
                       '</Response>',
        'token': '<?xml version="1.0" encoding="UTF-8" ?>'
                 '<Response>'
                 '  <Say language="%(locale)s">%(token)s</Say>'
                 '</Response>',
    }

    prompts = {
        # Translators: should be a language supported by Twilio,
        # see http://bit.ly/187I5cr
        'press_a_key': _('Hi, this is %(site_name)s calling. Press any key '
                         'to continue.'),

        # Translators: should be a language supported by Twilio,
        # see http://bit.ly/187I5cr
        'token': _('Your token is %(token)s. Repeat: %(token)s. Good bye.'),

        # Translators: should be a language supported by Twilio,
        # see http://bit.ly/187I5cr
        'no_input': _('You didn\'t press any keys. Good bye.')
    }

    def get(self, request, token):
        return self.create_response(self.templates['press_a_key'])

    def post(self, request, token):
        return self.create_response(self.templates['token'])

    def create_response(self, template):
        with translation.override(self.get_locale()):
            prompt_context = self.get_prompt_context()
            template_context = dict((k, v % prompt_context) for k, v in self.prompts.items())
            template_context['locale'] = self.get_twilio_locale()
            return HttpResponse(template % template_context, 'text/xml')

    def get_locale(self):
        locale = self.request.GET.get('locale', '')
        if not check_for_language(locale):
            locale = settings.LANGUAGE_CODE
        validate_voice_locale(locale)
        return locale

    def get_twilio_locale(self):
        # Translators: twilio_locale should be a locale supported by
        # Twilio, see http://bit.ly/187I5cr
        return pgettext('twilio_locale', 'en')

    def get_prompt_context(self):
        return {
            'site_name': get_current_site(self.request).name,

            # Build the prompt. The numbers have to be clearly pronounced,
            # this is by creating a string like "1. 2. 3. 4. 5. 6.", this way
            # Twilio reads the numbers one by one.
            'token': '. '.join(str(self.kwargs['token'])) if self.request.method == 'POST' else '',
        }
