from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.auth.views import logout

from two_factor.gateways.twilio.urls import urlpatterns as tf_twilio_urls
from two_factor.urls import urlpatterns as tf_urls

from .views import (
    ExampleSecretView, HomeView, RegistrationCompleteView, RegistrationView,
)

urlpatterns = [
    url(
        regex=r'^$',
        view=HomeView.as_view(),
        name='home',
    ),
    url(
        regex=r'^account/logout/$',
        view=logout,
        name='logout',
    ),
    url(
        regex=r'^secret/$',
        view=ExampleSecretView.as_view(),
        name='secret',
    ),
    url(
        regex=r'^account/register/$',
        view=RegistrationView.as_view(),
        name='registration',
    ),
    url(
        regex=r'^account/register/done/$',
        view=RegistrationCompleteView.as_view(),
        name='registration_complete',
    ),
    url(r'', include(tf_urls)),
    url(r'', include(tf_twilio_urls)),
    url(r'', include('user_sessions.urls', 'user_sessions')),
    url(r'^admin/', admin.site.urls),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ]
