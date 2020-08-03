from django.urls import re_path

from .views import TwilioCallApp

urlpatterns = ([
    re_path(
        r'^twilio/inbound/two_factor/(?P<token>\d+)/$',
        TwilioCallApp.as_view(),
        name='call_app',
    ),
], 'two_factor_twilio')
