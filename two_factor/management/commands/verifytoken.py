from binascii import hexlify
from django.contrib.auth.models import User
from django.core.management import BaseCommand, CommandError
from oath.totp import accept_totp

class Command(BaseCommand):
    args = '<username token>'
    help = 'Verify a generated token'

    def handle(self, *args, **options):
        if len(args) != 2:
            raise CommandError('Please provide a username and password')
        try:
            user = User.objects.get(username=args[0])
        except User.DoesNotExist:
            raise CommandError('User with username "%s" not found' % args[0])

        if not user.token:
            raise CommandError('User does not have a secret associated')

        accepted, drift = accept_totp(args[1], user.token.seed)

        if accepted:
            print 'Token accepted (clock drifted %s seconds)' % drift
        else:
            print 'Token not accepted'
