import logging

from django.core.exceptions import SuspiciousOperation
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from formtools.wizard.forms import ManagementForm
from formtools.wizard.storage.session import SessionStorage
from formtools.wizard.views import SessionWizardView

logger = logging.getLogger(__name__)


class ExtraSessionStorage(SessionStorage):
    """
    SessionStorage that includes the property `validated_step_data` for storing
    cleaned form data per step.
    """
    validated_step_data_key = 'validated_step_data'

    def init_data(self):
        super().init_data()
        self.data[self.validated_step_data_key] = {}

    def reset(self):
        if self.prefix in self.request.session:
            super().reset()
        else:
            self.init_data()

    def _get_validated_step_data(self):
        return self.data[self.validated_step_data_key]

    def _set_validated_step_data(self, validated_step_data):
        self.data[self.validated_step_data_key] = validated_step_data

    validated_step_data = property(_get_validated_step_data,
                                   _set_validated_step_data)


class IdempotentSessionWizardView(SessionWizardView):
    """
    WizardView that allows certain steps to be marked non-idempotent, in which
    case the form is only validated once and the cleaned values stored.
    """
    storage_name = 'two_factor.views.utils.ExtraSessionStorage'
    idempotent_dict = {}

    def is_step_visible(self, step):
        """
        Returns whether the given `step` should be included in the wizard; it
        is included if either the form is idempotent or not filled in before.
        """
        return self.idempotent_dict.get(step, True) or \
            step not in self.storage.validated_step_data

    def get_prev_step(self, step=None):
        """
        Returns the previous step before the given `step`. If there are no
        steps available, None will be returned. If the `step` argument is
        None, the current step will be determined automatically.
        """
        if step is None:
            step = self.steps.current
        form_list = self.get_form_list()
        keys = list(form_list.keys())
        key = keys.index(step) - 1
        if key >= 0:
            for prev_step in keys[key::-1]:
                if self.is_step_visible(prev_step):
                    return prev_step
        return None

    def get_next_step(self, step=None):
        """
        Returns the next step after the given `step`. If no more steps are
        available, None will be returned. If the `step` argument is None, the
        current step will be determined automatically.
        """
        if step is None:
            step = self.steps.current
        form_list = self.get_form_list()
        keys = list(form_list.keys())
        key = keys.index(step) + 1
        for next_step in keys[key:]:
            if self.is_step_visible(next_step):
                return next_step
        return None

    def post(self, *args, **kwargs):
        """
        Check if the current step is still available. It might not be if
        conditions have changed.
        """
        if self.steps.current not in self.steps.all:
            logger.warning("Current step '%s' is no longer valid, returning "
                           "to last valid step in the wizard.",
                           self.steps.current)
            return self.render_goto_step(self.steps.all[-1])

        # -- Duplicated code from upstream
        # Look for a wizard_goto_step element in the posted data which
        # contains a valid step name. If one was found, render the requested
        # form. (This makes stepping back a lot easier).
        wizard_goto_step = self.request.POST.get('wizard_goto_step', None)
        if wizard_goto_step and wizard_goto_step in self.get_form_list():
            return self.render_goto_step(wizard_goto_step)

        # Check if form was refreshed
        management_form = ManagementForm(self.request.POST, prefix=self.prefix)
        if not management_form.is_valid():
            raise SuspiciousOperation(_('ManagementForm data is missing or has been tampered with'))

        form_current_step = management_form.cleaned_data['current_step']
        if (form_current_step != self.steps.current
                and self.storage.current_step is not None):
            # form refreshed, change current step
            self.storage.current_step = form_current_step
        # -- End duplicated code from upstream

        # This is different from the first check, as this checks
        # if the new step is available. See issue #65.
        if self.steps.current not in self.steps.all:
            logger.warning("Requested step '%s' is no longer valid, returning "
                           "to last valid step in the wizard.",
                           self.steps.current)
            return self.render_goto_step(self.steps.all[-1])

        return super().post(*args, **kwargs)

    def process_step(self, form):
        """
        Stores the validated data for `form` and cleans out validated forms
        for next steps, as those might be affected by the current step. Note
        that this behaviour is relied upon by the `LoginView` to prevent users
        from bypassing the `TokenForm` by going steps back and changing
        credentials.
        """
        step = self.steps.current

        # If the form is not-idempotent (cannot be validated multiple times),
        # the cleaned data should be stored; marking the form as validated.
        self.storage.validated_step_data[step] = form.cleaned_data

        # It is assumed that earlier steps affect later steps; so even though
        # those forms might not be idempotent, we'll remove the validated data
        # to force re-entry.
        # form_list = self.get_form_list(idempotent=False)
        form_list = self.get_form_list()
        keys = list(form_list.keys())
        key = keys.index(step) + 1
        for next_step in keys[key:]:
            self.storage.validated_step_data.pop(next_step, None)

        return super().process_step(form)

    def render_done(self, form, **kwargs):
        """
        This method gets called when all forms passed. The method should also
        re-validate all steps to prevent manipulation. If any form don't
        validate, `render_revalidation_failure` should get called.
        If everything is fine call `done`.
        """
        final_form_list = []
        # walk through the form list and try to validate the data again.
        for form_key in self.get_form_list():
            form_obj = self.get_form(step=form_key,
                                     data=self.storage.get_step_data(form_key),
                                     files=self.storage.get_step_files(
                                         form_key))
            if not (form_key in self.idempotent_dict or form_obj.is_valid()):
                return self.render_revalidation_failure(form_key, form_obj,
                                                        **kwargs)
            final_form_list.append(form_obj)

        # render the done view and reset the wizard before returning the
        # response. This is needed to prevent from rendering done with the
        # same data twice.
        done_response = self.done(final_form_list, **kwargs)
        self.storage.reset()
        return done_response


def class_view_decorator(function_decorator):
    """
    Converts a function based decorator into a class based decorator usable
    on class based Views.

    Can't subclass the `View` as it breaks inheritance (super in particular),
    so we monkey-patch instead.

    From: http://stackoverflow.com/a/8429311/58107
    """
    def simple_decorator(View):
        View.dispatch = method_decorator(function_decorator)(View.dispatch)
        return View
    return simple_decorator
