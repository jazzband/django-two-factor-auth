Configuration
=============

General Settings
----------------

``TWO_FACTOR_PATCH_ADMIN`` (default: ``True``)
  Whether the Django admin is patched to use the default login view.

  .. warning::
     The admin currently does not enforce one-time passwords being set for
     admin users.

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
  Should point to a view that the user is redirected to after loging out. It was
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
  indefinately in a state of having entered their password successfully but not
  having passed two factor authentication. Set to ``0`` to disable.

``PHONENUMBER_DEFAULT_REGION`` (default: ``None``)
  The default region for parsing phone numbers. If your application's primary
  audience is a certain country, setting the region to that country allows
  entering phone numbers without that country's country code.

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
        url(r'', include(tf_twilio_urls)),
        ...
    ]

Additionally, you need to enable the ``ThreadLocals`` middleware:

.. code-block:: python

    MIDDLEWARE = (
        ...

        # Always include for two-factor auth
        'django_otp.middleware.OTPMiddleware',

        # Include for twilio gateway
        'two_factor.middleware.threadlocals.ThreadLocals',
    )


.. autoclass:: two_factor.gateways.twilio.gateway.Twilio

Fake Gateway
------------
.. autoclass:: two_factor.gateways.fake.Fake

.. _LOGIN_URL: https://docs.djangoproject.com/en/dev/ref/settings/#login-url
.. _LOGIN_REDIRECT_URL: https://docs.djangoproject.com/en/dev/ref/settings/#login-redirect-url
.. _LOGOUT_REDIRECT_URL: https://docs.djangoproject.com/en/dev/ref/settings/#logout-redirect-url
.. _Twilio: http://www.twilio.com/
.. _`Twilio client`: https://pypi.python.org/pypi/twilio
.. _python-qrcode: https://pypi.python.org/pypi/qrcode
.. _`the upstream ticket`: https://code.google.com/p/google-authenticator/issues/detail?id=327
