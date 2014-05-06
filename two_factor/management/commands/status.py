import django
from django.core.management.base import BaseCommand, CommandError

try:
    from django.contrib.auth import get_user_model
except ImportError:
    from django.contrib.auth.models import User
else:
    User = get_user_model()

from ...utils import default_device


class Command(BaseCommand):
    """
    Command to check two-factor authentication status for certain users.

    The command accepts any number of usernames, and will list if OTP is
    enabled or disabled for those users.

    Example usage::

        manage.py status bouke steve
        bouke: enabled
        steve: disabled
    """
    args = '<username username ...>'
    help = 'Checks two-factor authentication status for the given users'

    def handle(self, *args, **options):
        for username in args:
            try:
                user = User.objects.get_by_natural_key(username)
            except User.DoesNotExist:
                raise CommandError('User "%s" does not exist' % username)

            self._write('%s: %s' % (
                username,
                'enabled' if default_device(user) else self.style.ERROR('disabled')
            ))

    def _write(self, text):
        if django.VERSION >= (1, 5):
            self.stdout.write(text)
        else:
            self.stdout.write('%s\n' % text)
