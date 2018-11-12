"""Middleware to check if staff user has 2FA unabled."""

from django.shortcuts import redirect
from django.urls import resolve, reverse


class Enforce2FAMiddleware:
    """Enforce 2FA middleware."""
    def __init__(self, get_response):
        """Initialize the middleware."""
        self.get_response = get_response

    def __call__(self, request):
        """Wrap around actual Admin calls."""
        response = self.get_response(request)
        if resolve(request.path).app_name == 'two_factor' or (
                resolve(request.path).url_name == 'logout'):
            return response
        if not request.user.is_verified():
            return redirect(reverse('two_factor:profile'))
        return response
