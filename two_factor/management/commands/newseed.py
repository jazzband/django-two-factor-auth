import random
from django.contrib.auth.models import User
from django.core.management import BaseCommand, CommandError
from django.utils.http import urlencode
from two_factor.models import Token
from two_factor.util import generate_seed, get_qr_url

class Command(BaseCommand):
    args = '<username>'
    help = 'Set new seed for two-factor authentication'

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError('Provide a username as first argument')
        try:
            user = User.objects.get(username=args[0])
        except User.DoesNotExist:
            raise CommandError('User with username "%s" not found' % args[0])

        try:
            token = user.token
        except Token.DoesNotExist:
            token = Token(user=user)

        token.seed = generate_seed()
        token.save()

        print 'Updated seed for %s to: %s (hex)' % (user.username, token.seed)
        print ''
        print 'QR Code for Google Authenticator can be found here:'
        print ''
        print get_qr_url(user.username, token.seed)
        print ''
