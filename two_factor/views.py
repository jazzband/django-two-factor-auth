from datetime import timedelta
import urlparse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.formtools.wizard.views import SessionWizardView
from django.contrib.sites.models import get_current_site
from django.core.signing import Signer, BadSignature
from django.core.urlresolvers import reverse
from django.forms import Form
from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.template.response import TemplateResponse
from django.utils.datastructures import SortedDict
from django.utils.http import urlencode
from django.utils.timezone import now
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth import REDIRECT_FIELD_NAME, login as auth_login, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.conf import settings
from django.utils.translation import ugettext
from django.views.generic import FormView
from oath.totp import totp
from two_factor.call_gateways import call
from two_factor.forms import ComputerVerificationForm, MethodForm, TokenVerificationForm, PhoneForm, DisableForm
from two_factor.models import VerifiedComputer, Token
from two_factor.sms_gateways import send
from two_factor.util import generate_seed, get_qr_url, class_view_decorator

signer = Signer()

@sensitive_post_parameters()
@csrf_protect
@never_cache
def login(request, template_name='two_factor/login.html',
          redirect_field_name=REDIRECT_FIELD_NAME,
          authentication_form=AuthenticationForm,
          current_app=None, extra_context=None):
    """
    Displays the login form and handles the two factor login action.
    """
    redirect_to = request.REQUEST.get(redirect_field_name, '')
    netloc = urlparse.urlparse(redirect_to)[1]

    # Use default setting if redirect_to is empty
    if not redirect_to:
        redirect_to = settings.LOGIN_REDIRECT_URL

    # Heavier security check -- don't allow redirection to a different
    # host.
    elif netloc and netloc != request.get_host():
        redirect_to = settings.LOGIN_REDIRECT_URL

    if request.method == 'POST':
        form = authentication_form(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if hasattr(user, 'token'):
                params = {
                    redirect_field_name: redirect_to,
                    'user': signer.sign(user.pk),
                }
                return HttpResponseRedirect(
                    reverse('tf:verify') + '?' + urlencode(params)
                )
            else:
                # Okay, security checks complete. Log the user in.
                auth_login(request, user)

                if request.session.test_cookie_worked():
                    request.session.delete_test_cookie()

                return HttpResponseRedirect(redirect_to)

    else:
        form = authentication_form(request)

    request.session.set_test_cookie()

    current_site = get_current_site(request)

    context = {
        'form': form,
        redirect_field_name: redirect_to,
        'site': current_site,
        'site_name': current_site.name,
    }
    if extra_context is not None:
        context.update(extra_context)
    return TemplateResponse(request, template_name, context,
        current_app=current_app)

@sensitive_post_parameters()
@csrf_protect
@never_cache
def verify_computer(request, template_name='two_factor/verify_computer.html',
          redirect_field_name=REDIRECT_FIELD_NAME,
          computer_verification_form=ComputerVerificationForm,
          current_app=None, extra_context=None):

    redirect_to = request.REQUEST.get(redirect_field_name, '')
    netloc = urlparse.urlparse(redirect_to)[1]

    # Use default setting if redirect_to is empty
    if not redirect_to:
        redirect_to = settings.LOGIN_REDIRECT_URL

    # Heavier security check -- don't allow redirection to a different
    # host.
    elif netloc and netloc != request.get_host():
        redirect_to = settings.LOGIN_REDIRECT_URL

    try:
        user = User.objects.get(pk=signer.unsign(request.GET.get('user')))
    except (User.DoesNotExist, BadSignature):
        return HttpResponseRedirect(settings.LOGIN_URL)

    if request.method == 'POST':
        form = computer_verification_form(user=user, data=request.POST)
        if form.is_valid():
            # Okay, security checks complete. Log the user in.
            auth_login(request, user)

            if request.session.test_cookie_worked():
                request.session.delete_test_cookie()

            response = HttpResponseRedirect(redirect_to)

            # set computer verification
            if form.cleaned_data['remember']:
                vf = user.verifiedcomputer_set.create(
                    verified_until=now() + timedelta(days=30),
                    last_used_at=now(),
                    ip=request.META['REMOTE_ADDR'],
                )
                response.set_signed_cookie('computer', vf.id,
                    path=reverse('tf:verify'), max_age=30*86400, httponly=True)

            return response
    else:
        form = computer_verification_form(request, user)

        # has this computer been verified?
        try:
            computer_id = request.get_signed_cookie('computer', None)
            user = authenticate(user=user, computer_id=computer_id)
            if user and user.is_active:
                # Okay, security checks complete. Log the user in.
                auth_login(request, user)

                if request.session.test_cookie_worked():
                    request.session.delete_test_cookie()

                return HttpResponseRedirect(redirect_to)
        except VerifiedComputer.DoesNotExist:
            pass

        token = user.token
        if token.method in ('call', 'sms'):
            #todo use backup phone
            #todo resend message + throttling
            generated_token = totp(token.seed)
            if token.method == 'call':
                call(to=token.phone, request=request, token=generated_token)
            elif token.method == 'sms':
                send(to=token.phone, request=request, token=generated_token)

    current_site = get_current_site(request)

    context = {
        'form': form,
        redirect_field_name: redirect_to,
        'site': current_site,
        'site_name': current_site.name,
    }
    if extra_context is not None:
        context.update(extra_context)
    return TemplateResponse(request, template_name, context,
        current_app=current_app)


class Disable(FormView):
    template_name = 'two_factor/disable.html'
    form_class = DisableForm

    def get(self, request, *args, **kwargs):
        if not hasattr(self.request.user, 'token'):
            return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)
        return super(Disable, self).get(request, *args, **kwargs)

    def form_valid(self, form):
        if hasattr(self.request.user, 'token'):
            self.request.user.token.delete()
        self.request.user.verifiedcomputer_set.all().delete()
        return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)


@class_view_decorator(login_required)
class Enable(SessionWizardView):
    template_name = 'two_factor/enable.html'
    initial_dict = {}
    form_list = SortedDict([
        ('welcome', Form),
        ('method', MethodForm),
        ('generator', TokenVerificationForm),
        ('sms', PhoneForm),
        ('sms-verify', TokenVerificationForm),
        ('call', PhoneForm),
        ('call-verify', TokenVerificationForm),
    ])
    condition_dict = {
        'generator': lambda x: Enable.is_method(x, 'generator'),
        'sms': lambda x: Enable.is_method(x, 'sms'),
        'sms-verify': lambda x: Enable.is_method(x, 'sms'),
        'call': lambda x: Enable.is_method(x, 'call'),
        'call-verify': lambda x: Enable.is_method(x, 'call'),
    }

    @classmethod
    def get_initkwargs(cls, *args, **kwargs):
        return {}

    def is_method(self, method):
        cleaned_data = self.get_cleaned_data_for_step('method') or {}
        return cleaned_data.get('method') == method

    def get_form_data(self, step, field, default=None):
        cleaned_data = self.get_cleaned_data_for_step(step) or {}
        return cleaned_data.get(field, default)

    def get_form(self, step=None, data=None, files=None):
        form = super(Enable, self).get_form(step, data, files)
        if isinstance(form, TokenVerificationForm):
            form.seed = self.get_token().seed
        return form

    def get_token(self):
        if not 'token' in self.storage.data:
            alias = '%s@%s' % (self.request.user.username,
                               get_current_site(self.request).name)
            seed = generate_seed()
            self.storage.data['token'] = Token(
                seed=seed, user=self.request.user)
            self.storage.data['extra_data']['qr_url'] = get_qr_url(alias, seed)
        return self.storage.data['token']

    def get(self, request, *args, **kwargs):
        if hasattr(self.request.user, 'token'):
            return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)
        return super(Enable, self).get(request, *args, **kwargs)

    def done(self, form_list, **kwargs):
        form_data = [f.cleaned_data for f in form_list]
        token = self.get_token()
        token.method = form_data[1]['method']
        if token.method == 'sms':
            token.phone = form_data[2]['phone']
        elif token.method == 'call':
            token.phone = form_data[2]['phone']
        token.save()
        return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)

    def render_next_step(self, form, **kwargs):
        response = super(Enable, self).render_next_step(form, **kwargs)
        if self.steps.current in ['call-verify', 'sms-verify']:
            method = self.get_form_data('method', 'method')
            #todo use backup phone
            #todo resend message + throttling
            generated_token = totp(self.get_token().seed)
            if method == 'call':
                phone = self.get_form_data('call', 'phone')
                call(to=phone, request=self.request, token=generated_token)
            elif method == 'sms':
                phone = self.get_form_data('sms', 'phone')
                send(to=phone, request=self.request, token=generated_token)
        return response


@never_cache
def twilio_call_app(request):
    template = '<?xml version="1.0" encoding="UTF-8" ?>'\
               '<Response><Say>%(prompt)s</Say></Response>'
    prompt = ugettext('Hi, this is example.com calling. Please enter the '
                      'following code on your screen: %(token)s. Repeat: '
                      '%(token)s.')
    try:
        token = signer.unsign(request.GET.get('token'))
    except BadSignature:
        raise Http404
    template = template % {'prompt': prompt} % {'token': '. '.join(token)}
    return HttpResponse(template, 'text/xml')
