from django.conf.urls import url, include
from django.contrib.auth.views import logout

from two_factor.views import LoginView
from two_factor.urls import urlpatterns as tf_urls
from two_factor.gateways.twilio.urls import urlpatterns as tf_twilio_urls

from .views import SecureView


urlpatterns = [
    url(
        regex=r'^account/logout/$',
        view=logout,
        name='logout',
    ),
    url(
        regex=r'^account/custom-login/$',
        view=LoginView.as_view(redirect_field_name='next_page'),
        name='custom-login',
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

    url(r'', include(tf_urls + tf_twilio_urls, 'two_factor')),
]
