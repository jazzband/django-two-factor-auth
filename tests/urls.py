from django.contrib.auth.views import LogoutView
from django.urls import include, path

from two_factor.gateways.twilio.urls import urlpatterns as tf_twilio_urls
from two_factor.urls import urlpatterns as tf_urls
from two_factor.views import LoginView

from .views import SecureView

urlpatterns = [
    path(
        'account/logout/',
        LogoutView.as_view(),
        name='logout',
    ),
    path(
        'account/custom-field-name-login/',
        LoginView.as_view(redirect_field_name='next_page'),
        name='custom-field-name-login',
    ),
    path(
        'account/custom-allowed-success-url-login/',
        LoginView.as_view(
            success_url_allowed_hosts={'test.allowed-success-url.com'}
        ),
        name='custom-allowed-success-url-login',
    ),
    path(
        'account/custom-redirect-authenticated-user-login/',
        LoginView.as_view(
            redirect_authenticated_user=True
        ),
        name='custom-redirect-authenticated-user-login',
    ),

    path(
        'secure/',
        SecureView.as_view(),
    ),
    path(
        'secure/raises/',
        SecureView.as_view(raise_anonymous=True, raise_unverified=True),
    ),
    path(
        'secure/redirect_unverified/',
        SecureView.as_view(raise_anonymous=True,
                           verification_url='/account/login/'),
    ),
    path('', include(tf_urls)),
    path('', include(tf_twilio_urls)),
]
