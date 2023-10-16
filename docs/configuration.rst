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

WebAuthn Settings
-----------------

Start by providing a value for the following setting:

``TWO_FACTOR_WEBAUTHN_RP_NAME`` (default: ``None``)
  The human-palatable identifier for the `Relying Party`_. You **MUST** name your application. Failing to do so will
  raise an ``ImproperlyConfigured`` exception.
  
The defaults provided for all other settings should be enough to enable the use of fingerprint readers, security keys
and android phones (Chrome-based browsers only).

Tweak the following settings if you want to restrict the types of devices that can be used and the information that
will be sent to your application after the authentication takes place:

``TWO_FACTOR_WEBAUTHN_AUTHENTICATOR_ATTACHMENT`` (default: ``None``)
  The preferred `Authenticator Attachment`_ modality.
  Possible values: ``'platform'`` (like an embedded fingerprint reader), ``'cross-platform'`` (such as a usb security
  key). The default is to accept all attachment modalities.

``TWO_FACTOR_WEBAUTHN_PREFERRED_TRANSPORTS`` (default: ``None``)
  A list of preferred communication transports that will be set for all registered authenticators. **This can be
  used to optimize user interaction at authentication time. Its implementation is highly browser-dependent and may
  even be disregarded.**
  
  Chrome uses this to filter out credentials that do not use any of the transports listed.
  For example, if set to ``['usb', 'internal']`` Chrome will not attempt to authenticate the user with authenticators
  that communicate using CaBLE (e.g., android phones).
  
  Possible values for each element in the list are members of ``webauthn.helpers.structs.AuthenticatorTransport``. The
  default is to accept all transports.

``TWO_FACTOR_WEBAUTHN_UV_REQUIREMENT`` (default: ``'discouraged'``)
  The type of `User Verification`_ that is required. Verification ranges from a simple test of user presence such as
  by touching a button to more thorough checks like using biometrics or requiring user PIN input.
  Possible values: ``'discouraged'``, ``'preferred'``, ``'required'``.
  
``TWO_FACTOR_WEBAUTHN_ATTESTATION_CONVEYANCE`` (default: ``'none'``)
  The type of `Attestation Conveyance`_. A `Relying Party`_ may want to verify attestations to ensure that
  only authentication devices from certain approved vendors can be used. Depending on the level of conveyance, the
  attestation could include potentially identifying information, resulting in an additional prompt to the users so
  they can decide if they want to proceed.
  Possible values: ``'none'``, ``'indirect'`` and ``'direct'``. The ``'enterprise'`` conveyance type is not supported
  and will result in ``ImproperlyConfigured`` being raised.

  .. warning::
     Setting conveyance to other than ``'none'`` enables attestation verification against a list of root certificates.
     If the list of root certificates for a particular attestation statement format is empty, **then verification will
     always pass**.

     ``'fido-u2f'``, ``'packed'`` and ``'tpm'`` do not come pre-configured with root certificates. Download the
     additional certificates that you needed for your particular device and use the
     ``TWO_FACTOR_WEBAUTHN_PEM_ROOT_CERTS_BYTES_BY_FMT`` setting below.
  
``TWO_FACTOR_WEBAUTHN_PEM_ROOT_CERTS_BYTES_BY_FMT`` (default: ``None``)
  A mapping of attestation statement formats to lists of Root Certificates, provided as bytes. These will be used in
  addition to those already provided by ``py_webauthn`` to verify attestation objects.

  **Example:**
  
  If you want to verify attestations made by a Yubikey, get `Yubico's root CA`_ and use it as follows:

  .. code-block:: python

     yubico_u2f_ca = """
     -----BEGIN CERTIFICATE-----
     (Yubico's root CA goes here)
     -----END CERTIFICATE-----
     """

     root_ca_list = [yubico_u2f_ca.encode('ascii')]

     TWO_FACTOR_WEBAUTHN_PEM_ROOT_CERTS_BYTES_BY_FMT = {
         AttestationFormat.PACKED: root_ca_list,
         AttestationFormat.FIDO_U2F: root_ca_list,
     }

The following settings control how the attributes for WebAuthn entities are built: 

``TWO_FACTOR_WEBAUTHN_ENTITIES_FORM_MIXIN`` (default: ``'two_factor.webauthn.utils.WebauthnEntitiesFormMixin'``)
  A mixin to provide WebAuthn entities (user and `Relying Party`_) needed during setup and authentication. Although
  the default works in most cases you can provide your own methods to build the different attributes that
  are required by these entities (e.g., if you use a custom `User` model).

``TWO_FACTOR_WEBAUTHN_RP_ID`` (default: ``None``)
  The default form mixin uses this setting to specify the domain of the `Relying Party`_. By default, the relying
  party ID is ``None`` i.e. the current domain returned by `HttpRequest.get_host()`_ will be used. You may want to set
  it to a higher-level domain if your application has several sub-domains (e.g., ``www.example.com`` for web and
  ``m.example.com`` for the mobile version, meaning you may want to set this value to ``'example.com'`` so credentials
  are valid for both versions).

WebAuthn devices support throttling too:

``TWO_FACTOR_WEBAUTHN_THROTTLE_FACTOR`` (default: ``1``)
  This controls the rate of throttling. The sequence of 1, 2, 4, 8... seconds is
  multiplied by this factor to define the delay imposed after 1, 2, 3, 4...
  successive failures. Set to ``0`` to disable throttling completely.

.. _`Relying Party`: https://w3c.github.io/webauthn/#webauthn-relying-party
.. _`Authenticator Attachment`: https://www.w3.org/TR/webauthn/#enum-attachment
.. _`User Verification`: https://www.w3.org/TR/webauthn-2/#enum-userVerificationRequirement
.. _`Attestation Conveyance`: https://www.w3.org/TR/webauthn-2/#enum-attestation-convey
.. _`Yubico's Root CA`: https://developers.yubico.com/U2F/Attestation_and_Metadata/
.. _`HttpRequest.get_host()`: https://docs.djangoproject.com/en/4.0/ref/request-response/#django.http.HttpRequest.get_host

Remember Browser
----------------

During a successful login with a token, the user may choose to remember this browser.
If the same user logs in again on the same browser, a token will not be requested, as the browser
serves as a second factor.

The option to remember a browser is deactivated by default. Set `TWO_FACTOR_REMEMBER_COOKIE_AGE` to activate.

The browser will be remembered as long as:

- the cookie that authorizes the browser did not expire,
- the user did not reset the password, and
- the device initially used to authorize the browser is still valid.

The browser is remembered by setting a signed 'remember cookie'.

In order to invalidate remembered browsers after password resets,
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
