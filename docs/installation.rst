Installation
============

You can install from PyPI_ using ``pip`` to install  ``django-two-factor-auth``
and its dependencies::

    ``pip install django-two-factor-auth``

Add the following apps to the ``INSTALLED_APPS``::

    INSTALLED_APPS = (
        ...
        'django_otp',
        'django_otp.plugins.otp_static',
        'django_otp.plugins.otp_totp',
        'two_factor',
    )

Add the ``django-otp`` middleware to your ``MIDDLEWARE_CLASSES``. Make sure
it comes after ``AuthenticationMiddleware``::

    MIDDLEWARE_CLASSES = (
        ...
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django_otp.middleware.OTPMiddleware',
        ...
    )

Point to the new login pages in your settings::

    from django.core.urlresolvers import reverse_lazy

    LOGIN_URL = reverse_lazy('two_factor:login')

    # this one is optional
    LOGIN_REDIRECT_URL = reverse_lazy('two_factor:profile')

Add the routes to your url configuration::

    urlpatterns = patterns(
        '',
        url(r'', include('two_factor.urls', 'two_factor')),
        ...
    )

.. warning::
   Be sure to remove any other login routes, otherwise the two-factor
   authentication might be circumvented. The admin interface should be
   automatically patched to use the new login method.

Yubikey
-------

In order to support Yubikeys, you have to install a plugin for `django-otp`::

    pip install django-otp-yubikey

Add the following app to the ``INSTALLED_APPS``::

    INSTALLED_APPS = (
        ...
        'otp_yubikey',
    )

This plugin also requires adding a validation service, through wich YubiKeys
will be verified. Normally, you'd use the YubiCloud for this. In the Django
admin, navigate to ``YubiKey validation services`` and add an item. Django
Two-Factor Authentication will identify the validation service with the
name ``default``. The other fields can be left empty, but you might want to
consider requesting an API ID along with API key and using SSL for
communicating with YubiCloud.

You could also do this using this snippet::

    manage.py shell
    >>> from otp_yubikey.models import ValidationService
    >>> ValidationService.objects.create(name='default', use_ssl=True, 
    ...     param_sl='', param_timeout='')
    <ValidationService: default>
