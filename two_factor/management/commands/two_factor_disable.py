from django.core.management.base import BaseCommand, CommandError
try:
    from django.contrib.auth import get_user_model
except ImportError:
    from django.contrib.auth.models import User
else:
    User = get_user_model()

from django_otp import devices_for_user


class Command(BaseCommand):
    """
    Command for disabling two-factor authentication for certain users.

    The command accepts any number of usernames, and will remove all OTP
    devices for those users.

    Example usage::

        manage.py disable bouke steve
    """
    args = '<username username ...>'
    help = 'Disables two-factor authentication for the given users'

    def handle(self, *args, **options):
        for username in args:
            try:
                user = User.objects.get_by_natural_key(username)
            except User.DoesNotExist:
                raise CommandError('User "%s" does not exist' % username)

            for device in devices_for_user(user):
                device.delete()
