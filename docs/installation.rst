Installation
============

You can install from PyPI_ using ``pip`` to install ``django-two-factor-auth``
and its dependencies:

.. code-block:: console

    $ pip install django-two-factor-auth

This project uses ``django-phonenumber-field`` which requires either ``phonenumbers``
or ``phonenumberslite`` to be installed. Either manually install a supported version
using ``pip`` or install ``django-two-factor-auth`` with the extras specified as in
the below examples:

.. code-block:: console

    $ pip install django-two-factor-auth[phonenumbers]

    OR

    $ pip install django-two-factor-auth[phonenumberslite]

Setup
-----

Add the following apps to the ``INSTALLED_APPS``:

.. code-block:: python

    INSTALLED_APPS = [
        ...
        'django_otp',
        'django_otp.plugins.otp_static',
        'django_otp.plugins.otp_totp',
        'django_otp.plugins.otp_email',  # <- for email capability.
        'otp_yubikey',  # <- for yubikey capability.
        'two_factor',
        'two_factor.plugins.phonenumber',  # <- for phone number capability.
        'two_factor.plugins.email',  # <- for email capability.
        'two_factor.plugins.yubikey',  # <- for yubikey capability.
    ]

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
       path('', include(tf_urls)),
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

    INSTALLED_APPS = [
        ...
        'otp_yubikey',
        'two_factor.plugins.yubikey',
    ]

This plugin also requires adding a validation service, through which YubiKeys
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

.. _webauthn-setup:

WebAuthn Setup
--------------

In order to support WebAuthn_ devices, you have to install the py_webauthn_ package.
It's a ``django-two-factor-auth`` extra so you can select it at install time:

.. code-block:: console

    $ pip install django-two-factor-auth[webauthn]

You need to include the plugin in your Django settings:

.. code-block:: python

    INSTALLED_APPS = [
        ...
        'two_factor.plugins.webauthn',
    ]

WebAuthn also requires your service to be reachable using HTTPS.
An exception is made if the domain is ``localhost``, which can be served using plain HTTP.

If you use a different domain, don't forget to set ``SECURE_PROXY_SSL_HEADER`` in your Django settings accordingly:

.. code-block:: python

    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

You can try a WebAuthn-enabled version of the example app that is reachable at http://localhost:8000:

.. code-block:: console

    $ make example-webauthn

.. _PyPI: https://pypi.python.org/pypi/django-two-factor-auth
.. _Yubikeys: https://www.yubico.com/products/yubikey-hardware/
.. _WebAuthn: https://www.w3.org/TR/webauthn/
.. _py_webauthn: https://pypi.org/project/webauthn/
