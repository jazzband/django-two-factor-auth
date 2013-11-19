import django


if django.VERSION[:2] >= (1, 6):
    from django.contrib.formtools.wizard.views import WizardView
    from django.contrib.formtools.wizard.views import SessionWizardView
    from django.contrib.formtools.wizard.storage.session import SessionStorage
    from django.utils.http import is_safe_url
    from django.utils.module_loading import import_by_path

else:
    import sys
    try:
        from urllib.parse import urlparse
    except ImportError:
        from urlparse import urlparse

    from django import forms
    from django.core.exceptions import ImproperlyConfigured
    from django.forms import formsets
    from django.utils import six
    from django.utils.importlib import import_module
    from django.utils.datastructures import SortedDict

    from django.contrib.formtools.wizard.storage.exceptions import NoFileStorageConfigured
    from django.contrib.formtools.wizard.views import WizardView as _WizardView


    # Fix for Django 1.4 and 1.5 which don't allow setting form_list etc on the
    # class but require them to be passed in the urlconf.
    class WizardView(_WizardView):
        @classmethod
        def get_initkwargs(cls, form_list=None, initial_dict=None,
            instance_dict=None, condition_dict=None, *args, **kwargs):
            """
            Creates a dict with all needed parameters for the form wizard instances.

            * `form_list` - is a list of forms. The list entries can be single form
              classes or tuples of (`step_name`, `form_class`). If you pass a list
              of forms, the wizardview will convert the class list to
              (`zero_based_counter`, `form_class`). This is needed to access the
              form for a specific step.
            * `initial_dict` - contains a dictionary of initial data dictionaries.
              The key should be equal to the `step_name` in the `form_list` (or
              the str of the zero based counter - if no step_names added in the
              `form_list`)
            * `instance_dict` - contains a dictionary whose values are model
              instances if the step is based on a ``ModelForm`` and querysets if
              the step is based on a ``ModelFormSet``. The key should be equal to
              the `step_name` in the `form_list`. Same rules as for `initial_dict`
              apply.
            * `condition_dict` - contains a dictionary of boolean values or
              callables. If the value of for a specific `step_name` is callable it
              will be called with the wizardview instance as the only argument.
              If the return value is true, the step's form will be used.
            """

            kwargs.update({
                'initial_dict': initial_dict or kwargs.pop('initial_dict',
                    getattr(cls, 'initial_dict', None)) or {},
                'instance_dict': instance_dict or kwargs.pop('instance_dict',
                    getattr(cls, 'instance_dict', None)) or {},
                'condition_dict': condition_dict or kwargs.pop('condition_dict',
                    getattr(cls, 'condition_dict', None)) or {}
            })

            form_list = form_list or kwargs.pop('form_list',
                getattr(cls, 'form_list', None)) or []

            computed_form_list = SortedDict()

            assert len(form_list) > 0, 'at least one form is needed'

            # walk through the passed form list
            for i, form in enumerate(form_list):
                if isinstance(form, (list, tuple)):
                    # if the element is a tuple, add the tuple to the new created
                    # sorted dictionary.
                    computed_form_list[six.text_type(form[0])] = form[1]
                else:
                    # if not, add the form with a zero based counter as unicode
                    computed_form_list[six.text_type(i)] = form

            # walk through the new created list of forms
            for form in six.itervalues(computed_form_list):
                if issubclass(form, formsets.BaseFormSet):
                    # if the element is based on BaseFormSet (FormSet/ModelFormSet)
                    # we need to override the form variable.
                    form = form.form
                # check if any form contains a FileField, if yes, we need a
                # file_storage added to the wizardview (by subclassing).
                for field in six.itervalues(form.base_fields):
                    if (isinstance(field, forms.FileField) and
                            not hasattr(cls, 'file_storage')):
                        raise NoFileStorageConfigured(
                            "You need to define 'file_storage' in your "
                            "wizard view in order to handle file uploads.")

            # build the kwargs for the wizardview instances
            kwargs['form_list'] = computed_form_list
            return kwargs

        def render_goto_step(self, goto_step, **kwargs):
            """
            This method gets called when the current step has to be changed.
            `goto_step` contains the requested step to go to.
            """
            self.storage.current_step = goto_step
            form = self.get_form(
                data=self.storage.get_step_data(self.steps.current),
                files=self.storage.get_step_files(self.steps.current))
            return self.render(form)


    def is_safe_url(url, host=None):
        """
        Return ``True`` if the url is a safe redirection (i.e. it doesn't point to
        a different host and uses a safe scheme).

        Always returns ``False`` on an empty url.
        """
        if not url:
            return False
        url_info = urlparse(url)
        return (not url_info.netloc or url_info.netloc == host) and \
               (not url_info.scheme or url_info.scheme in ['http', 'https'])


    def import_by_path(dotted_path, error_prefix=''):
        """
        Import a dotted module path and return the attribute/class designated by the
        last name in the path. Raise ImproperlyConfigured if something goes wrong.
        """
        try:
            module_path, class_name = dotted_path.rsplit('.', 1)
        except ValueError:
            raise ImproperlyConfigured("%s%s doesn't look like a module path" % (
                error_prefix, dotted_path))
        try:
            module = import_module(module_path)
        except ImportError as e:
            msg = '%sError importing module %s: "%s"' % (
                error_prefix, module_path, e)
            six.reraise(ImproperlyConfigured, ImproperlyConfigured(msg),
                        sys.exc_info()[2])
        try:
            attr = getattr(module, class_name)
        except AttributeError:
            raise ImproperlyConfigured('%sModule "%s" does not define a "%s" attribute/class' % (
                error_prefix, module_path, class_name))
        return attr


if (1, 5) <= django.VERSION[:2] < (1, 6):
    from django.contrib.formtools.wizard.storage.session import SessionStorage

    # Need to override SessionWizardView to subclass from the backported
    # WizardView.
    class SessionWizardView(WizardView):
        storage_name = 'django.contrib.formtools.wizard.storage.session.SessionStorage'

else:
    from django.contrib.formtools.wizard.storage.session import SessionStorage as _SessionStorage
    from django.core import urlresolvers

    # Fix for Django 1.4 -- it does `return .. or {}`, which makes working with
    # the extra_data very cumbersome
    class SessionStorage(_SessionStorage):
        def _get_extra_data(self):
            return self.data[self.extra_data_key]


    # Use the fixed SessionStorage
    class SessionWizardView(WizardView):
        """
        A WizardView with pre-configured SessionStorage backend.
        """
        storage_name = 'two_factor.compat.SessionStorage'
