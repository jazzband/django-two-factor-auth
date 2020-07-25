from django.urls import re_path

from two_factor.views import (
    BackupTokensView, DisableView, LoginView, PhoneDeleteView, PhoneSetupView,
    ProfileView, QRGeneratorView, SetupCompleteView, SetupView,
)

core = [
    re_path(
        r'^account/login/$',
        LoginView.as_view(),
        name='login',
    ),
    re_path(
        r'^account/two_factor/setup/$',
        SetupView.as_view(),
        name='setup',
    ),
    re_path(
        r'^account/two_factor/qrcode/$',
        QRGeneratorView.as_view(),
        name='qr',
    ),
    re_path(
        r'^account/two_factor/setup/complete/$',
        SetupCompleteView.as_view(),
        name='setup_complete',
    ),
    re_path(
        r'^account/two_factor/backup/tokens/$',
        BackupTokensView.as_view(),
        name='backup_tokens',
    ),
    re_path(
        r'^account/two_factor/backup/phone/register/$',
        PhoneSetupView.as_view(),
        name='phone_create',
    ),
    re_path(
        r'^account/two_factor/backup/phone/unregister/(?P<pk>\d+)/$',
        PhoneDeleteView.as_view(),
        name='phone_delete',
    ),
]

profile = [
    re_path(
        r'^account/two_factor/$',
        ProfileView.as_view(),
        name='profile',
    ),
    re_path(
        r'^account/two_factor/disable/$',
        DisableView.as_view(),
        name='disable',
    ),
]

urlpatterns = (core + profile, 'two_factor')
