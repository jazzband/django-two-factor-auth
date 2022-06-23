from django.urls import path

from two_factor.admin import TwoFactorAdminSite

from .urls import urlpatterns

urlpatterns += [
    path('admin/', TwoFactorAdminSite().urls),
]
