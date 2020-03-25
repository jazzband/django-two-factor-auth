from django.conf.urls import include, url
from django.contrib.auth.views import LogoutView

from two_factor.gateways.twilio.urls import urlpatterns as tf_twilio_urls
from two_factor.urls import urlpatterns as tf_urls
from two_factor.views import LoginView

from .views import SecureView

urlpatterns = [
    url(
        regex=r'^account/logout/$',
        view=LogoutView.as_view(),
        name='logout',
    ),
    url(
        regex=r'^account/custom-field-name-login/$',
        view=LoginView.as_view(redirect_field_name='next_page'),
        name='custom-field-name-login',
    ),
    url(
        regex=r'^account/custom-allowed-success-url-login/$',
        view=LoginView.as_view(
            success_url_allowed_hosts={'test.allowed-success-url.com'}
        ),
        name='custom-allowed-success-url-login',
    ),
    url(
        regex=r'^account/custom-redirect-authenticated-user-login/$',
        view=LoginView.as_view(
            redirect_authenticated_user=True
        ),
        name='custom-redirect-authenticated-user-login',
    ),

    url(
        regex=r'^secure/$',
        view=SecureView.as_view(),
    ),
    url(
        regex=r'^secure/raises/$',
        view=SecureView.as_view(raise_anonymous=True, raise_unverified=True),
    ),
    url(
        regex=r'^secure/redirect_unverified/$',
        view=SecureView.as_view(raise_anonymous=True,
                                verification_url='/account/login/'),
    ),
    url(r'', include(tf_urls)),
    url(r'', include(tf_twilio_urls)),
]
