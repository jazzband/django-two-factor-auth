from django.test import TestCase

from tests.utils import UserMixin
from two_factor.plugins.phonenumber.method import PhoneCallMethod, SMSMethod


class PhoneMethodBaseTestMixin(UserMixin):
    def test_get_devices(self):
        other_method_code = PhoneCallMethod.code if isinstance(self.method, SMSMethod) else SMSMethod.code
        user = self.create_user()
        backup_device = user.phonedevice_set.create(name='backup', number='+12024561111', method=self.method.code)
        default_device = user.phonedevice_set.create(name='default', number='+12024561111', method=self.method.code)
        user.phonedevice_set.create(name='default', number='+12024561111', method=other_method_code)

        method_device_pks = [device.pk for device in self.method.get_devices(user)]
        self.assertEqual(method_device_pks, [backup_device.pk, default_device.pk])


class PhoneCallMethodTest(PhoneMethodBaseTestMixin, TestCase):
    method = PhoneCallMethod()


class SMSMethodTest(PhoneMethodBaseTestMixin, TestCase):
    method = SMSMethod()
