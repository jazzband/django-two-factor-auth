# coding=utf8
from django.contrib.auth.decorators import login_required
from django.contrib.sites.models import get_current_site
from django.template.response import TemplateResponse
from django.views.decorators.cache import never_cache
from django.views.generic import TemplateView

class Home(TemplateView):
    template_name = 'demo/home.html'

@never_cache
@login_required
def profile(request, template_name='demo/profile.html',
            current_app=None, extra_context=None):
    current_site = get_current_site(request)

    context = {
        'user': request.user,
        'site': current_site,
        'site_name': current_site.name
    }

    if extra_context is not None:
        context.update(extra_context)
    return TemplateResponse(request, template_name, context,
        current_app=current_app)
