from django.dispatch import Signal

user_verified = Signal(providing_args=['request', 'user', 'device'])
