from django.contrib.sites.models import get_current_site
from django.http import HttpResponse
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.cache import never_cache
from django.views.generic import View

from .utils import class_view_decorator


@class_view_decorator(never_cache)
class TwilioCallApp(View):
    template = '<?xml version="1.0" encoding="UTF-8" ?>' \
               '<Response><Say>%(prompt)s</Say></Response>'

    prompt = _('Hi, this is %(site_name)s calling. Please enter the '
               'following code on your screen: %(token)s. Repeat: '
               '%(token)s.')

    def get(self, request, token):
        # Build the prompt. The numbers have to be clearly pronounced, this is
        # by creating a string like "1. 2. 3. 4. 5. 6.", this way Twilio reads
        # the numbers one by one.
        prompt = self.prompt % {
            'token': '. '.join(token),
            'site_name': get_current_site(request).name,
        }
        prompt = self.template % {
            'prompt': prompt,
        }
        return HttpResponse(prompt, 'text/xml')
