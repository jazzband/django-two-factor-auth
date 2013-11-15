import logging

logger = logging.getLogger(__name__)


class Fake(object):
    @staticmethod
    def make_call(device, token):
        logger.info('Fake call to %s: "Your token is: %s"', device.number, token)

    @staticmethod
    def send_sms(device, token):
        logger.info('Fake SMS to %s: "Your token is: %s"', device.number, token)
