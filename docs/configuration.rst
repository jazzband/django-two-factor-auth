Configuration
=============

General Settings
----------------

``TWO_FACTOR_PATCH_ADMIN`` (default: ``True``)
  Whether the Django admin is patched to use the default login view.

  .. warning::
     The admin currently does not enforce one-time passwords being set for
     admin users.

``LOGIN_URL``
  Should point to the login view provided by this application as described in
  setup. This login view handles password authentication followed by a one-time
  password exchange if enabled for that account. This can be a URL path or URL
  name as defined in the Django documentation.

  See also LOGIN_URL_.

``LOGIN_REDIRECT_URL``
  This application provides a basic page for managing one's account. This view
  is entirely optional and could be implemented in a custom view. This can be a
  URL path or URL name as defined in the Django documentation.

  See also LOGIN_REDIRECT_URL_.

``LOGOUT_REDIRECT_URL``
  Should point to a view that the user is redirected to after logging out. It was
  added in Django 1.10, and also adapted by this application. This can be a
  URL path or URL name as defined in the Django documentation.

  See also LOGOUT_REDIRECT_URL_.

``TWO_FACTOR_QR_FACTORY``
  The default generator for the QR code images is set to SVG. This
  does not require any further dependencies, however it does not work
  on IE8 and below. If you have PIL, Pillow or pyimaging installed
  you may wish to use PNG images instead.

  * ``'qrcode.image.pil.PilImage'`` may be used for PIL/Pillow
  * ``'qrcode.image.pure.PymagingImage'`` may be used for pyimaging

  For more QR factories that are available see python-qrcode_.

``TWO_FACTOR_TOTP_DIGITS`` (default: ``6``)
  The number of digits to use for TOTP tokens, can be set to 6 or 8. This
  setting will be used for tokens delivered by phone call or text message and
  newly configured token generators. Existing token generator devices will not
  be affected.

  .. warning::
     The Google Authenticator app does not support 8 digit codes (see
     `the upstream ticket`_). Don't set this option to 8 unless all of your
     users use a 8 digit compatible token generator app.

``TWO_FACTOR_LOGIN_TIMEOUT`` (default ``600``)
  The number of seconds between a user successfully passing the "authentication"
  step (usually by entering a valid username and password) and them having to
  restart the login flow and re-authenticate. This ensures that users can't sit
  indefinitely in a state of having entered their password successfully but not
  having passed two factor authentication. Set to ``0`` to disable.

Phone-related settings
----------------------

If you want to enable phone methods to send tokens to users, make sure that
``'two_factor.plugins.phonenumber'`` is present in your ``INSTALLED_APPS``
setting. Then, you may want to configure the following settings:

``TWO_FACTOR_CALL_GATEWAY`` (default: ``None``)
  Which gateway to use for making phone calls. Should be set to a module or
  object providing a ``make_call`` method. Currently two gateways are bundled:

  * ``'two_factor.gateways.twilio.gateway.Twilio'`` for making real phone calls using
    Twilio_.
  * ``'two_factor.gateways.fake.Fake'``  for development, recording tokens to the
    default logger.

``TWO_FACTOR_SMS_GATEWAY`` (default: ``None``)
  Which gateway to use for sending text messages. Should be set to a module or
  object providing a ``send_sms`` method. Currently two gateways are bundled:

  * ``'two_factor.gateways.twilio.gateway.Twilio'`` for sending real text messages using
    Twilio_.
  * ``'two_factor.gateways.fake.Fake'``  for development, recording tokens to the
    default logger.

``PHONENUMBER_DEFAULT_REGION`` (default: ``None``)
  The default region for parsing phone numbers. If your application's primary
  audience is a certain country, setting the region to that country allows
  entering phone numbers without that country's country code.

``TWO_FACTOR_PHONE_THROTTLE_FACTOR`` (default: ``1``)
  This controls the rate of throttling. The sequence of 1, 2, 4, 8... seconds is
  multiplied by this factor to define the delay imposed after 1, 2, 3, 4...
  successive failures. Set to ``0`` to disable throttling completely.

Email Gateway
-------------

To enable receiving authentication tokens by email, you have to add
``'django_otp.plugins.otp_totp'`` to your ``INSTALLED_APPS`` setting. Also
ensure that the DEFAULT_FROM_EMAIL_ settings is configured with an appropriate
value.

Read the `Email Settings`_ section of the ``django_otp`` documentation to find
about possible email-related customizations (subject/body of messages,
throttling, etc.).

Twilio Gateway
--------------
To use the Twilio gateway, you need first to install the `Twilio client`_:

.. code-block:: console

    $ pip install twilio

Next, add additional urls to your config:

.. code-block:: python

    # urls.py
    from two_factor.gateways.twilio.urls import urlpatterns as tf_twilio_urls
    
    urlpatterns = [
        path('', include(tf_twilio_urls)),
        ...
    ]

Additionally, you need to enable the ``ThreadLocals`` middleware:

.. code-block:: python

    MIDDLEWARE = (
        ...

        # Always include for two-factor auth
        'django_otp.middleware.OTPMiddleware',

        # Include for Twilio gateway
        'two_factor.middleware.threadlocals.ThreadLocals',
    )


.. autoclass:: two_factor.gateways.twilio.gateway.Twilio

Fake Gateway
------------
.. autoclass:: two_factor.gateways.fake.Fake

.. _LOGIN_URL: https://docs.djangoproject.com/en/dev/ref/settings/#login-url
.. _LOGIN_REDIRECT_URL: https://docs.djangoproject.com/en/dev/ref/settings/#login-redirect-url
.. _LOGOUT_REDIRECT_URL: https://docs.djangoproject.com/en/dev/ref/settings/#logout-redirect-url
.. _DEFAULT_FROM_EMAIL: https://docs.djangoproject.com/en/stable/ref/settings/#default-from-email
.. _`Email Settings`: https://django-otp-official.readthedocs.io/en/stable/overview.html#email-settings
.. _Twilio: http://www.twilio.com/
.. _`Twilio client`: https://pypi.python.org/pypi/twilio
.. _python-qrcode: https://pypi.python.org/pypi/qrcode
.. _`the upstream ticket`: https://code.google.com/p/google-authenticator/issues/detail?id=327

Remember Browser
----------------

During a successful login with a token, the user may choose to remember this browser.
If the same user logs in again on the same browser, a token will not be requested, as the browser
serves as a second factor.

The option to remember a browser is deactived by default. Set `TWO_FACTOR_REMEMBER_COOKIE_AGE` to activate.

The browser will be remembered as long as:

- the cookie that authorizes the browser did not expire,
- the user did not reset the password, and
- the device initially used to authorize the browser is still valid.

The browser is remembered by setting a signed 'remember cookie'.

In order to invalidate remebered browsers after password resets,
the package relies on the `password` field of the `User` model.
Please consider this in case you do not use the `password` field
e.g. [django-auth-ldap](https://github.com/django-auth-ldap/django-auth-ldap)

``TWO_FACTOR_REMEMBER_COOKIE_AGE``
  Age in seconds to remember the browser. The remember cookie will expire after the given time interval
  and the server will not accept this cookie to remember this browser, user, and device any longer.

  If this is set to a positive `int` the user is presented the option to remember the browser when entering the token.
  If the age is `None`, the user must authenticate with a token option during each login, if a device is setup.

  Default: `None`

``TWO_FACTOR_REMEMBER_COOKIE_PREFIX``
  Prefix of the remember cookie.
  It prefixes a uuid4 to allow multiple remember cookies on the same browser for multiple users.

  Default: `'remember-cookie_'`


``TWO_FACTOR_REMEMBER_COOKIE_DOMAIN``
  The domain to be used when setting the remember cookie.

  Only relevant if `TWO_FACTOR_REMEMBER_COOKIE_AGE` is not `None`.

  Default: `None`

``TWO_FACTOR_REMEMBER_COOKIE_PATH``
  The path of the remember cookie.

  Only relevant if `TWO_FACTOR_REMEMBER_COOKIE_AGE` is not `None`.

  Default: `'/'`

``TWO_FACTOR_REMEMBER_COOKIE_SECURE``
  Whether the remember cookie should be secure (https:// only).

  Only relevant if `TWO_FACTOR_REMEMBER_COOKIE_AGE` is not `None`.

  Default: `False`

``TWO_FACTOR_REMEMBER_COOKIE_HTTPONLY``
  Whether to use the non-RFC standard httpOnly flag (IE, FF3+, others)

  Only relevant if `TWO_FACTOR_REMEMBER_COOKIE_AGE` is not `None`.

  Default: `True`

``TWO_FACTOR_REMEMBER_COOKIE_SAMESITE``
  Whether to set the flag restricting cookie leaks on cross-site requests.
  This can be 'Lax', 'Strict', or None to disable the flag.

  Only relevant if `TWO_FACTOR_REMEMBER_COOKIE_AGE` is not `None`.

  Default: `'Lax'`


