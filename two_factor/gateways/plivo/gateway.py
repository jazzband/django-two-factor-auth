import plivo
from django.conf import settings
from django.template.loader import render_to_string


class Plivo:
    """
    Gateway for sending text messages using Plivo.
    """

    def __init__(self):
        self.client = plivo.RestClient(
            auth_id=getattr(settings, 'PLIVO_AUTH_ID'),
            auth_token=getattr(settings, 'PLIVO_AUTH_TOKEN')
        )
        self.source_number = getattr(settings, 'PLIVO_SOURCE_NUMBER')

    def make_call(self, device, token):
        raise NotImplementedError

    def send_sms(self, device, token):
        text = render_to_string(
            'two_factor/plivo/sms_message.html',
            {'token': token}
        )
        send_kwargs = {
            'src': self.source_number,
            'dst': device.number.as_e164,
            'text': text,
        }

        self.client.messages.create(**send_kwargs)
