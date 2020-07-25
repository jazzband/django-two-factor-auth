from django.urls import re_path

from two_factor.admin import AdminSiteOTPRequired

from .urls import urlpatterns

otp_admin_site = AdminSiteOTPRequired()

urlpatterns += [
    re_path(r'^otp_admin/', otp_admin_site.urls),
]
