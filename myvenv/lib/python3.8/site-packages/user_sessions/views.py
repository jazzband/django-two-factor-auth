from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, resolve_url
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from django.views.generic import DeleteView, ListView, View
from django.views.generic.edit import DeletionMixin


class SessionMixin(object):
    def get_queryset(self):
        return self.request.user.session_set\
            .filter(expire_date__gt=now()).order_by('-last_activity')


class LoginRequiredMixin(object):
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(LoginRequiredMixin, self).dispatch(request, *args,
                                                        **kwargs)


class SessionListView(LoginRequiredMixin, SessionMixin, ListView):
    """
    View for listing a user's own sessions.

    This view shows list of a user's currently active sessions. You can
    override the template by providing your own template at
    `user_sessions/session_list.html`.
    """
    def get_context_data(self, **kwargs):
        kwargs['session_key'] = self.request.session.session_key
        return super(SessionListView, self).get_context_data(**kwargs)


class SessionDeleteView(LoginRequiredMixin, SessionMixin, DeleteView):
    """
    View for deleting a user's own session.

    This view allows a user to delete an active session. For example log
    out a session from a computer at the local library or a friend's place.
    """
    def delete(self, request, *args, **kwargs):
        if kwargs['pk'] == request.session.session_key:
            logout(request)
            next_page = getattr(settings, 'LOGOUT_REDIRECT_URL', '/')
            return redirect(resolve_url(next_page))
        return super(SessionDeleteView, self).delete(request, *args, **kwargs)

    def get_success_url(self):
        return str(reverse_lazy('user_sessions:session_list'))


class SessionDeleteOtherView(LoginRequiredMixin, SessionMixin, DeletionMixin, View):
    """
    View for deleting all user's sessions but the current.

    This view allows a user to delete all other active session. For example
    log out all sessions from a computer at the local library or a friend's
    place.
    """
    def get_object(self):
        return super(SessionDeleteOtherView, self).get_queryset().\
            exclude(session_key=self.request.session.session_key)

    def get_success_url(self):
        return str(reverse_lazy('user_sessions:session_list'))
