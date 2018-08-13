from django.dispatch import Signal, receiver

from two_factor.views.core import LoginView
from two_factor.views.utils import login_alerts

user_verified = Signal(providing_args=['request', 'user', 'device'])
login_alert = Signal(providing_args=['request'])


@receiver(login_alert, sender=LoginView)
def login_alert(sender, **kwargs):
    login_alerts(kwargs['request'])
