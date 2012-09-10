# coding=utf-8
from django.contrib.auth.models import User
from oath import accept_totp

class TokenBackend(object):
    def authenticate(self, user, token):
        accepted, drift = accept_totp(token, user.secret.seed)
        return user if accepted else None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None


class VerifiedComputerBackend(object):
    def authenticate(self, user, computer_id):

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
        verification = user.verifiedcomputer_set.get(pk=computer_id)
        return user if verification.verified_until > now() else None
