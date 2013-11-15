from django.conf.urls import patterns, include, url
from django.contrib import admin

from .views import (exampleSecretView, HomeView, RegistrationView,
                    RegistrationCompleteView)


admin.autodiscover()

urlpatterns = patterns(
    '',
    url(
        regex=r'^$',
        view=HomeView.as_view(),
        name='home',
    ),
    url(
        regex=r'^account/logout/$',
        view='django.contrib.auth.views.logout',
        name='logout',
    ),
    url(
        regex=r'^secret/$',
        view=exampleSecretView.as_view(),
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
    url(r'', include('two_factor.urls', 'two_factor')),
    url(r'^admin/', include(admin.site.urls)),
)
