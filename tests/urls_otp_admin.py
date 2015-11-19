from django.conf.urls import url, include

from two_factor.admin import AdminSiteOTPRequired

from .urls import urlpatterns


otp_admin_site = AdminSiteOTPRequired()

urlpatterns += [
    url(r'^otp_admin/', include(otp_admin_site.urls)),
]
