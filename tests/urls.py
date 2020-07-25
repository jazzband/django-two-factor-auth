from django.contrib.auth.views import LogoutView
from django.urls import include, re_path

from two_factor.gateways.twilio.urls import urlpatterns as tf_twilio_urls
from two_factor.urls import urlpatterns as tf_urls
from two_factor.views import LoginView

from .views import SecureView

urlpatterns = [
    re_path(
        r'^account/logout/$',
        LogoutView.as_view(),
        name='logout',
    ),
    re_path(
        r'^account/custom-field-name-login/$',
        LoginView.as_view(redirect_field_name='next_page'),
        name='custom-field-name-login',
    ),
    re_path(
        r'^account/custom-allowed-success-url-login/$',
        LoginView.as_view(
            success_url_allowed_hosts={'test.allowed-success-url.com'}
        ),
        name='custom-allowed-success-url-login',
    ),
    re_path(
        r'^account/custom-redirect-authenticated-user-login/$',
        LoginView.as_view(
            redirect_authenticated_user=True
        ),
        name='custom-redirect-authenticated-user-login',
    ),

    re_path(
        r'^secure/$',
        SecureView.as_view(),
    ),
    re_path(
        r'^secure/raises/$',
        SecureView.as_view(raise_anonymous=True, raise_unverified=True),
    ),
    re_path(
        r'^secure/redirect_unverified/$',
        SecureView.as_view(raise_anonymous=True,
                           verification_url='/account/login/'),
    ),
    re_path(r'', include(tf_urls)),
    re_path(r'', include(tf_twilio_urls)),
]
