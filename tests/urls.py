from django.conf.urls import patterns, url, include
from django.contrib import admin

from two_factor.admin import AdminSiteOTPRequired
from two_factor.views import LoginView
from two_factor.urls import urlpatterns as tf_urls
from two_factor.gateways.twilio.urls import urlpatterns as tf_twilio_urls

from .views import SecureView

admin.autodiscover()
otp_admin_site = AdminSiteOTPRequired()

urlpatterns = patterns(
    '',
    url(
        regex=r'^account/logout/$',
        view='django.contrib.auth.views.logout',
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
    url(r'^admin/', include(admin.site.urls)),
    url(r'^otp_admin/', include(otp_admin_site.urls)),
)
