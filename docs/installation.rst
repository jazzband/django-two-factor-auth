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
