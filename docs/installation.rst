Installation
============

You can install from PyPI_ using ``pip`` to install ``django-two-factor-auth``
and its dependencies:

.. code-block:: console

    $ pip install django-two-factor-auth

Setup
-----

Add the following apps to the ``INSTALLED_APPS``:

.. code-block:: python

    INSTALLED_APPS = (
        ...
        'django_otp',
        'django_otp.plugins.otp_static',
        'django_otp.plugins.otp_totp',
        'two_factor',
    )

Add the ``django-otp`` middleware to your ``MIDDLEWARE``. Make sure
it comes after ``AuthenticationMiddleware``:

.. code-block:: python

    MIDDLEWARE = (
        ...
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django_otp.middleware.OTPMiddleware',
        ...
    )

Point to the new login pages in your ``settings.py``:

.. code-block:: python

    LOGIN_URL = 'two_factor:login'

    # this one is optional
    LOGIN_REDIRECT_URL = 'two_factor:profile'

Add the routes to your project url configuration:

.. code-block:: python

    from two_factor.urls import urlpatterns as tf_urls
    urlpatterns = [
       url(r'', include(tf_urls)),
        ...
    ]

.. warning::
   Be sure to remove any other login routes, otherwise the two-factor
   authentication might be circumvented. The admin interface should be
   automatically patched to use the new login method.

Yubikey Setup
-------------

In order to support Yubikeys_, you have to install a plugin for `django-otp`:

.. code-block:: console

    $ pip install django-otp-yubikey

Add the following app to the ``INSTALLED_APPS``:

.. code-block:: python

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

You could also do this using Django's `manage.py shell`:

.. code-block:: console

    $ python manage.py shell

.. code-block:: python

    >>> from otp_yubikey.models import ValidationService
    >>> ValidationService.objects.create(
    ...     name='default', use_ssl=True, param_sl='', param_timeout=''
    ... )
    <ValidationService: default>

.. _PyPI: https://pypi.python.org/pypi/django-two-factor-auth
.. _Yubikeys: https://www.yubico.com/products/yubikey-hardware/
