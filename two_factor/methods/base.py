from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _


class Method:
    code = None
    verbose_name = None
    form_path = None

    @property
    def form_class(self):
        return import_string(self.form_path)

    def setup_done(self, wizard, form_list):
        device = wizard.get_device()
        device.save()
        return device


class GeneratorMethod(Method):
    code = 'generator'
    verbose_name = _('Token generator')
    form_path = 'two_factor.forms.TOTPDeviceForm'

    def is_available(self):
        return True

    def setup_done(self, wizard, form_list):
        form = [form for form in form_list if isinstance(form, self.form_class)][0]
        device = form.save()
        return device


class MethodRegistry:
    _methods = []

    def __init__(self):
        self.register(GeneratorMethod())

    def register(self, method):
        self._methods.append(method)

    def unregister(self, code):
        self._methods = [m for m in self._methods if m.code != code]

    def get_method(self, code):
        try:
            return [meth for meth in self._methods if meth.code == code][0]
        except IndexError:
            return None

    def get_methods(self):
        return self._methods

    def get_phone_methods(self):
        return [meth for meth in self._methods if meth.code in ['call', 'sms']]
