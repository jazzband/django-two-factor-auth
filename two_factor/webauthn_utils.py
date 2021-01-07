import os
import cbor2
from binascii import b2a_hex

from hashlib import sha1

from django.conf import settings
from webauthn import webauthn
from webauthn.webauthn import _webauthn_b64_encode, _webauthn_b64_decode

from two_factor.models import WebauthnDevice


def make_challenge():
    return _webauthn_b64_encode(os.urandom(32)).decode('utf-8')


def make_user_id(user):
    hashed_id = sha1(str(user.pk).encode('utf-8')).hexdigest().encode('utf-8')
    return _webauthn_b64_encode(hashed_id).decode('utf-8')


def get_response_key_format(response):
    att_obj = cbor2.loads(_webauthn_b64_decode(response['attObj']))
    return att_obj.get('fmt')


def get_device_used_in_response(user, response):
    target_credentials_id = response['id'].rstrip('=')
    try:
        return WebauthnDevice.objects.get(user=user, key_handle=target_credentials_id)
    except WebauthnDevice.DoesNotExist:
        return None


def make_credentials_options(user, relying_party):
    """
    Used for registering a new WebAuthn device: send a request to be passed to navigator.credentials.create
    :param user: the django user adding the device
    :param relying_party: a dictionary representing the relying party, with `name` and `id`
    :return: a WebAuthnMakeCredentialOptions object
    """
    credentials_options = webauthn.WebAuthnMakeCredentialOptions(
        challenge=make_challenge(),
        rp_name=relying_party['name'],
        rp_id=relying_party['id'],
        user_id=make_user_id(user),
        username=user.get_username(),
        display_name=user.get_full_name(),
        icon_url=None
    ).registration_dict

    # Currently the webauthn lib does not support this property, so we need to inject it
    user_verification = 'required' if settings.TWO_FACTOR_WEBAUTHN_UV_REQUIRED else 'discouraged'
    credentials_options['authenticatorSelection'] = {'userVerification': user_verification}

    return credentials_options


def make_registration_response(request, response, relying_party, origin):
    """
    Builds a WebAuthn Registration Response (result of the navigator.credentials.create), to be validated
    :param request: the request sent to the user
    :param response: the response received from the user
    :param relying_party: the relying party, with `id`
    :param origin: the origin expected
    :return: a WebAuthnRegistrationResponse object, with a `verify` method on it
    """
    # We need to "fix" some keys in the response, as the WebAuthn library we use read some weird keys
    response['clientData'] = response.get('clientData', response.get('clientDataJSON'))
    response['attObj'] = response.get('attObj', response.get('attestationObject'))
    return webauthn.WebAuthnRegistrationResponse(
        rp_id=relying_party['id'],
        origin=origin,
        registration_response=response,
        challenge=request['challenge'],
        trust_anchor_dir=settings.TWO_FACTOR_WEBAUTHN_TRUSTED_ATTESTATION_ROOT,
        trusted_attestation_cert_required=settings.TWO_FACTOR_WEBAUTHN_TRUSTED_ATTESTATION_CERT_REQUIRED,
        self_attestation_permitted=settings.TWO_FACTOR_WEBAUTHN_SELF_ATTESTATION_PERMITTED,
        uv_required=settings.TWO_FACTOR_WEBAUTHN_UV_REQUIRED,
    )


def make_user(user, device, relying_party):
    return webauthn.WebAuthnUser(
        user_id=make_user_id(user),
        username=user.get_username(),
        display_name=user.get_full_name(),
        icon_url=None,
        credential_id=device.key_handle,
        public_key=device.public_key,
        sign_count=device.sign_count,
        rp_id=relying_party['id'],
    )


def make_assertion_options(user, relying_party):
    """
    Build a WebAuthnAssertionOptions for user login (to be passed to navigator.credentials.get)
    :param user: the django user logging in
    :param relying_party: a dictionary representing the relying party, with `id`
    :return: A dict that can be JSON-serialized, to be sent to the client
    """
    webauthn_assertion_options = webauthn.WebAuthnAssertionOptions(
        [make_user(user, device, relying_party) for device in user.webauthn_keys.all()],
        challenge=make_challenge()
    ).assertion_dict

    # Currently the webauthn lib does not support this property, so we need to inject it
    user_verification = 'required' if settings.TWO_FACTOR_WEBAUTHN_UV_REQUIRED else 'discouraged'
    webauthn_assertion_options['userVerification'] = user_verification

    return webauthn_assertion_options


def make_assertion_response(user, relying_party, origin, device, request, response):
    """
    Build a WebAuthnAssertionResponse, to validate the result of navigator.credentials.get
    :param user: the django user logging in
    :param relying_party: a dictionary representing the relying party, with `id`
    :param origin: the origin expected
    :param device: the device used for authenticating
    :param request: the request sent to the user
    :param response: the response from the user
    :return: a WebAuthnAssertionResponse object, with a verify method
    """
    # We need to "fix" some keys in the response, as the WebAuthn library we use read some weird keys
    response['clientData'] = response.get('clientData', response.get('clientDataJSON'))
    response['attObj'] = response.get('attObj', response.get('attestationObject'))
    response['authData'] = response.get('authData', response.get('authenticatorData'))
    response['signature'] = b2a_hex(_webauthn_b64_decode(response['signature']))

    webauthn_assertion_response = webauthn.WebAuthnAssertionResponse(
        webauthn_user=make_user(user, device, relying_party),
        assertion_response=response,
        challenge=request['challenge'],
        origin=origin,
        uv_required=settings.TWO_FACTOR_WEBAUTHN_UV_REQUIRED,
    )

    return webauthn_assertion_response
