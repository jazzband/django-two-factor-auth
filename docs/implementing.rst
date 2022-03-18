Implementing
============
Users can opt-in to enhanced security by enabling two-factor authentication.
There is currently no enforcement of a policy, it is entirely optional.
However, you could override this behaviour to enforce a custom policy.

Limiting access to certain views
--------------------------------
For increased security views can be limited to two-factor-enabled users. This
allows you to secure certain parts of the website. Doing so requires a
decorator, class mixin or a custom inspection of a user's session.

Decorator
~~~~~~~~~
You can use django-otp's built-in :meth:`~django_otp.decorators.otp_required`
decorator to limit access to two-factor-enabled users::

    from django_otp.decorators import otp_required

    @otp_required
    def my_view(request):
        pass

Mixin
~~~~~
The mixin :class:`~two_factor.views.mixins.OTPRequiredMixin` can be used to
limit access to class-based views (CBVs)::

    class ExampleSecretView(OTPRequiredMixin, TemplateView):
        template_name = 'secret.html'

Custom
~~~~~~
The method ``is_verified()`` is added through django-otp's
:class:`~django_otp.middleware.OTPMiddleware` which can be used to check if the
user was logged in using two-factor authentication::

    def my_view(request):
        if request.user.is_verified():
            # user logged in using two-factor
            pass
        else:
            # user not logged in using two-factor
            pass


Enforcing two-factor
--------------------
Forcing users to enable two-factor authentication is not implemented. However,
you could create your own custom policy.


Admin Site
----------
By default the admin login is patched to use the login views provided by this
application. Patching the admin is required as users would otherwise be able
to circumvent OTP verification. See also :data:`~two_factor.TWO_FACTOR_PATCH_ADMIN`.
Be aware that certain packages include their custom login views, for example
`django.contrib.admindocs`. When using said packages, OTP verification
can be circumvented. Thus however the normal admin login view is patched,
OTP might not always be enforced on the admin views. See the next paragraph
on how to do this.

.. _Hooking AdminSite instances into your URLconf:
   https://docs.djangoproject.com/en/dev/ref/contrib/admin/#hooking-adminsite-instances-into-your-urlconf

In order to only allow verified users (enforce OTP) to access the admin pages,
you have to use a custom admin site. You can either use
:class:`~two_factor.admin.AdminSiteOTPRequired` or
:class:`~two_factor.admin.AdminSiteOTPRequiredMixin`. See also the Django
documentation on `Hooking AdminSite instances into your URLconf`_.

If you want to enforce two factor authentication in the admin and use the
default admin site (e.g.  because 3rd party packages register to
``django.contrib.admin.site``) you can monkey patch the default ``AdminSite``
with this. In your ``urls.py``::

    from django.contrib import admin
    from two_factor.admin import AdminSiteOTPRequired

    admin.site.__class__ = AdminSiteOTPRequired

    urlpatterns = [
        path('admin/', admin.site.urls),
        ...
    ]


Signals
-------
When a user was successfully verified using a OTP, the signal
:data:`~two_factor.signals.user_verified` is sent. The signal includes the
user, the device used and the request itself. You can use this signal for
example to warn a user when one of his backup tokens was used::

    from django.contrib.sites.shortcuts import get_current_site
    from django.dispatch import receiver
    from two_factor.signals import user_verified


    @receiver(user_verified)
    def test_receiver(request, user, device, **kwargs):
        current_site = get_current_site(request)
        if device.name == 'backup':
            message = 'Hi %(username)s,\n\n'\
                      'You\'ve verified yourself using a backup device '\
                      'on %(site_name)s. If this wasn\'t you, your '\
                      'account might have been compromised. You need to '\
                      'change your password at once, check your backup '\
                      'phone numbers and generate new backup tokens.'\
                      % {'username': user.get_username(),
                         'site_name': current_site.name}
            user.email_user(subject='Backup token used', message=message)

