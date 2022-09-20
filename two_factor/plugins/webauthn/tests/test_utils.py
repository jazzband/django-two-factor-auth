import json
from unittest import skipUnless

from django.test import TestCase

try:
    import webauthn
    from webauthn.helpers import bytes_to_base64url
    from webauthn.helpers.structs import (
        PublicKeyCredentialRpEntity, PublicKeyCredentialUserEntity,
    )

    from two_factor.plugins.webauthn.utils import (
        make_credential_creation_options, make_credential_request_options,
    )
except ImportError:
    webauthn = None


@skipUnless(webauthn, 'package webauthn is not present')
class UtilsTests(TestCase):
    def setUp(self):
        super().setUp()
        self.mocked_user = PublicKeyCredentialUserEntity(
            id=b'mocked-user-id', name='mocked-username', display_name='Mocked Display Name')
        self.mocked_rp = PublicKeyCredentialRpEntity(id='mocked-rp-id', name='mocked-rp-name')
        self.mocked_challenge = bytes_to_base64url(b'mocked-challenge')
        self.mocked_user_id_b64 = bytes_to_base64url(b'mocked-user-id')
        self.mocked_credential_id_b64 = bytes_to_base64url(b'mocked-credential-id')

    def test_make_credential_creation_options(self):
        json_options, challenge_b64 = make_credential_creation_options(
            self.mocked_user, self.mocked_rp, [self.mocked_credential_id_b64], challenge=self.mocked_challenge)
        options = json.loads(json_options)

        self.assertEquals(options['rp'], {'id': self.mocked_rp.id, 'name': self.mocked_rp.name})
        self.assertEquals(
            options['user'],
            {'id': self.mocked_user_id_b64, 'name': 'mocked-username', 'displayName': 'Mocked Display Name'},
        )
        self.assertEquals(options['challenge'], self.mocked_challenge)
        self.assertEquals(options['excludeCredentials'], [{'type': 'public-key', 'id': self.mocked_credential_id_b64}])
        self.assertEquals(
            options['authenticatorSelection'],
            {'requireResidentKey': False, 'userVerification': 'discouraged'},
        )
        self.assertEquals(options['attestation'], 'none')
        self.assertEquals(challenge_b64, self.mocked_challenge)

    def test_make_credential_request_options(self):
        json_options, challenge_b64 = make_credential_request_options(
            self.mocked_rp, [self.mocked_credential_id_b64], challenge=self.mocked_challenge)
        options = json.loads(json_options)

        self.assertEquals(options['rpId'], self.mocked_rp.id)
        self.assertEquals(options['challenge'], self.mocked_challenge)
        self.assertEquals(len(options['allowCredentials']), 1)
        self.assertEquals(options['allowCredentials'][0]['type'], 'public-key')
        self.assertEquals(options['allowCredentials'][0]['id'], self.mocked_credential_id_b64)
        self.assertEquals(options['userVerification'], 'discouraged')
        self.assertEquals(challenge_b64, self.mocked_challenge)
