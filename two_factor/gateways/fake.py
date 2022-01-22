import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class Fake:
    """
    Prints the tokens to the logger. You will have to set the message level of
    the ``two_factor`` logger to ``INFO`` for them to appear in the console.
    Useful for local development. You should configure your logging like this::

        LOGGING = {
            'version': 1,
            'disable_existing_loggers': False,
            'handlers': {
                'console': {
                    'level': 'DEBUG',
                    'class': 'logging.StreamHandler',
                },
            },
            'loggers': {
                'two_factor': {
                    'handlers': ['console'],
                    'level': 'INFO',
                }
            }
        }
    """
    @staticmethod
    def make_call(device, token):
        logger.info('Fake call to %s: "Your token is: %s"', device.number.as_e164, token)

    @staticmethod
    def send_sms(device, token):
        logger.info('Fake SMS to %s: "Your token is: %s"', device.number.as_e164, token)


class QueryableFake(object):
    """A Fake gateway that can be queried.

    For example, you may use this in your unit tests::

        >>> from django.test import TestCase, override_settings
        >>> from django.contrib.auth import get_user_model
        >>> from django.conf import settings
        >>> from two_factor.gateways.fake import QueryableFake
        >>> from two_factor.models import PhoneDevice
        >>> from phonenumber_field.phonenumber import PhoneNumber
        >>>
        >>> class MyTestCase(TestCase):
        ...     def tearDown(self):
        ...         QueryableFake.reset()
        ...
        ...     @override_settings(
        ...         TWO_FACTOR_SMS_GATEWAY='two_factor.gateways.fake.QueryableFake',
        ...     )
        ...     def test_something(self):
        ...        user = get_user_model().objects.create(...)
        ...        PhoneDevice.objects.create(
        ...            user=user, name='default', method='sms',
        ...            number=PhoneNumber.from_string('+441234567890'),
        ...        )
        ...        self.client.post(settings.LOGIN_URL,
        ...            'username': user.username,
        ...            'password': 'password',
        ...        })
        ...        token = QueryableFake.sms_tokens['+441234567890'].pop()
        ...        self.client.post(settings.LOGIN_URL, {'token': token})
    """
    sms_tokens = defaultdict(list)
    call_tokens = defaultdict(list)

    @classmethod
    def clear_all_tokens(cls):
        cls.sms_tokens = defaultdict(list)
        cls.call_tokens = defaultdict(list)
    reset = clear_all_tokens

    @classmethod
    def make_call(cls, device, token):
        cls.call_tokens[str(device.number)].append(token)

    @classmethod
    def send_sms(cls, device, token):
        cls.sms_tokens[str(device.number)].append(token)
