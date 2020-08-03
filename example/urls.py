from django.conf import settings
from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.urls import include, re_path

from two_factor.gateways.twilio.urls import urlpatterns as tf_twilio_urls
from two_factor.urls import urlpatterns as tf_urls

from .views import (
    ExampleSecretView, HomeView, RegistrationCompleteView, RegistrationView,
)

urlpatterns = [
    re_path(
        r'^$',
        HomeView.as_view(),
        name='home',
    ),
    re_path(
        r'^account/logout/$',
        LogoutView.as_view(),
        name='logout',
    ),
    re_path(
        r'^secret/$',
        ExampleSecretView.as_view(),
        name='secret',
    ),
    re_path(
        r'^account/register/$',
        RegistrationView.as_view(),
        name='registration',
    ),
    re_path(
        r'^account/register/done/$',
        RegistrationCompleteView.as_view(),
        name='registration_complete',
    ),
    re_path(r'', include(tf_urls)),
    re_path(r'', include(tf_twilio_urls)),
    re_path(r'', include('user_sessions.urls', 'user_sessions')),
    re_path(r'^admin/', admin.site.urls),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [
        re_path(r'^__debug__/', include(debug_toolbar.urls)),
    ]
