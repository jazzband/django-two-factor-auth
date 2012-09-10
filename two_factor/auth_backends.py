# coding=utf-8
from django.contrib.auth.models import User
from oath import accept_totp

class TokenBackend(object):
    def authenticate(self, user, token):
        accepted, drift = accept_totp(token, user.secret.secret)
        return user if accepted else None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
