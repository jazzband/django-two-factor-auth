from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.sites.models import get_current_site
from django.shortcuts import render, redirect
from django.template.response import TemplateResponse
from django.views.decorators.cache import never_cache
from django.views.generic import TemplateView
from two_factor.models import VerifiedComputer


class Home(TemplateView):
    template_name = 'demo/home.html'


def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect(settings.LOGIN_URL)
    else:
        form = UserCreationForm()

    return render(request, 'demo/register.html', {
        'form': form,
    })


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


@never_cache
@login_required
def remove_computer_verification(request, id):
    if request.method == 'POST':
        try:
            request.user.verifiedcomputer_set.get(id=id).delete()
        except VerifiedComputer.DoesNotExist:
            pass
    return redirect(profile)
