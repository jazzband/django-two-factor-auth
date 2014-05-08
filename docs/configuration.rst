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

  * ``two_factor.gateways.twilio.gateway.Twilio`` for making real phone calls using
    Twilio_.
  * ``two_factor.gateways.fake.Fake``  for development, recording tokens to the
    default logger.

``TWO_FACTOR_SMS_GATEWAY`` (default: ``None``)
  Which gateway to use for sending text messages. Should be set to a module or
  object providing a ``send_sms`` method. Currently two gateways are bundled:

  * ``two_factor.gateways.twilio.gateway.Twilio`` for sending real text messages using
    Twilio_.
  * ``two_factor.gateways.fake.Fake``  for development, recording tokens to the
    default logger.

``LOGIN_URL``
  Should point to the login view provided by this application. This login view
  handles password authentication followed by a one-time password exchange if
  enabled for that account.

  See also LOGIN_URL_.

``LOGIN_REDIRECT_URL``
  This application provides a basic page for managing one's account. This view
  is entirely optional and could be implemented in a custom view.

  See also LOGIN_REDIRECT_URL_.

``TWO_FACTOR_QR_FACTORY``
  The default generator for the QR code images is set to SVG. This
  does not require any further dependencies, however it does not work
  on IE8 and below. If you have PIL, Pillow or pyimaging installed
  you may wish to use PNG images instead.

  * ``qrcode.image.pil.PilImage`` may be used for PIL/Pillow
  * ``qrcode.image.pure.PymagingImage`` may be used for pyimaging
  
  For more QR factories that are available see python-qrcode_.

Twilio Gateway
--------------
To use the Twilio gateway, you need first to install the `Twilio client`_::

    pip install twilio

Next, you also need to include the Twilio urlpatterns. As these urlpatterns are
all defined using a single Django namespace, these should be joined with the
base urlpatterns, like so::

    # urls.py
    from two_factor.urls import urlpatterns as tf_urls
    from two_factor.gateways.twilio.urls import urlpatterns as tf_twilio_urls

    urlpatterns = patterns('',
        url(r'', include(tf_urls + tf_twilio_urls, 'two_factor')),
    )

.. autoclass:: two_factor.gateways.twilio.gateway.Twilio

Fake Gateway
------------
.. autoclass:: two_factor.gateways.fake.Fake

.. _LOGIN_URL: https://docs.djangoproject.com/en/dev/ref/settings/#login-url
.. _LOGIN_REDIRECT_URL: https://docs.djangoproject.com/en/dev/ref/settings/#login-redirect-url
.. _Twilio: http://www.twilio.com/
.. _`Twilio client`: https://pypi.python.org/pypi/twilio
.. _python-qrcode: https://pypi.python.org/pypi/qrcode
