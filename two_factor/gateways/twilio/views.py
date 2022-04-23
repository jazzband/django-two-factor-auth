from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.http import HttpResponse
from django.template import Context, Engine
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
                       '    <Say language="{{ locale }}">{{ press_a_key }}</Say>'
                       '  </Gather>'
                       '  <Say language="{{ locale }}">{{ no_input }}</Say>'
                       '</Response>',
        'token': '<?xml version="1.0" encoding="UTF-8" ?>'
                 '<Response>'
                 '  <Say language="{{ locale }}">{{ your_token_is }}</Say>'
                 '  <Pause>'
                 '{% for digit in token %}  <Say language="{{ locale }}">{{ digit }}</Say>'
                 '  <Pause>{% endfor %}'
                 '  <Say language="{{ locale }}">{{ repeat }}</Say>'
                 '  <Pause>'
                 '{% for digit in token %}  <Say language="{{ locale }}">{{ digit }}</Say>'
                 '  <Pause>{% endfor %}'
                 '  <Say language="{{ locale }}">{{ goodbye }}</Say>'
                 '</Response>',
    }

    prompts = {
        # Translators: should be a language supported by Twilio,
        # see http://bit.ly/187I5cr
        'press_a_key': _('Hi, this is %(site_name)s calling. Press any key '
                         'to continue.'),

        # Translators: should be a language supported by Twilio,
        # see http://bit.ly/187I5cr
        'no_input': _('You didn’t press any keys. Good bye.'),

        # Translators: should be a language supported by Twilio,
        # see http://bit.ly/187I5cr
        'your_token_is': _('Your token is:'),

        # Translators: should be a language supported by Twilio,
        # see http://bit.ly/187I5cr
        'repeat': _('Repeat:'),

        # Translators: should be a language supported by Twilio,
        # see http://bit.ly/187I5cr
        'goodbye': _('Good bye.'),
    }

    def get(self, request, token):
        return self.create_response(self.templates['press_a_key'])

    def post(self, request, token):
        return self.create_response(self.templates['token'])

    def create_response(self, template_str):
        template = Engine().from_string(template_str)
        with translation.override(self.get_locale()):
            prompt_context = self.get_prompt_context()
            template_context = {k: v % prompt_context for k, v in self.prompts.items()}
            template_context['locale'] = self.get_twilio_locale()
            template_context['token'] = list(str(self.kwargs['token'])) if self.request.method == 'POST' else ''
            return HttpResponse(template.render(Context(template_context)), content_type='text/xml')

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
        }
