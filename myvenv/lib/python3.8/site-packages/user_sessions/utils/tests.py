from django.conf import settings
from django.contrib.auth import authenticate, login
from django.http import HttpRequest
from django.test import Client as BaseClient

from ..backends.db import SessionStore


class Client(BaseClient):
    """
    Custom implementation of django.test.Client.

    It is required to perform tests that require to login in sites using
    django-user-sessions since its implementation of SessionStore has to
    required parameters which is not in concordance with what is expected
    from the original Client
    """
    def login(self, **credentials):
        """
        Sets the Factory to appear as if it has successfully logged into a site.

        Returns True if login is possible; False if the provided credentials
        are incorrect, or the user is inactive, or if the sessions framework is
        not available.
        """
        user = authenticate(**credentials)
        if user and user.is_active:
            # Create a fake request to store login details.
            request = HttpRequest()
            request.user = None
            if self.session:
                request.session = self.session
            else:
                request.session = SessionStore(user_agent='Python/2.7', ip='127.0.0.1')
            login(request, user)

            # Save the session values.
            request.session.save()

            # Set the cookie to represent the session.
            session_cookie = settings.SESSION_COOKIE_NAME
            self.cookies[session_cookie] = request.session.session_key
            cookie_data = {
                'max-age': None,
                'path': '/',
                'domain': settings.SESSION_COOKIE_DOMAIN,
                'secure': settings.SESSION_COOKIE_SECURE or None,
                'expires': None,
            }
            self.cookies[session_cookie].update(cookie_data)

            return True
        else:
            return False

    def logout(self):
        """
        Removes the authenticated user's cookies and session object.

        Causes the authenticated user to be logged out.
        """
        session_cookie = self.cookies.get(settings.SESSION_COOKIE_NAME)
        if session_cookie:
            if self.session:
                self.session.delete(session_cookie)
            del self.cookies[settings.SESSION_COOKIE_NAME]

    def _session(self):
        """
        Obtains the current session variables.
        """
        if 'user_sessions' in settings.INSTALLED_APPS:
            cookie = self.cookies.get(settings.SESSION_COOKIE_NAME, None)
            if cookie:
                return SessionStore(session_key=cookie.value,
                                    user_agent='Python/2.7', ip='127.0.0.1')
    session = property(_session)
