from django.urls import path

from two_factor.admin import AdminSiteOTPRequired

from .urls import urlpatterns

otp_admin_site = AdminSiteOTPRequired()

urlpatterns += [
    path('otp_admin/', otp_admin_site.urls),
]
