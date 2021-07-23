from django.conf.urls import url

from two_factor.views import (
    BackupTokensView, DisableView, LoginView, PhoneDeleteView, PhoneSetupView,
    ProfileView, QRGeneratorView, SetupCompleteView, SetupView,
)

core = [
    url(
        r'^two_factor/login/$',
        LoginView.as_view(),
        name='login',
    ),
    url(
        r'^two_factor/setup/$',
        SetupView.as_view(),
        name='setup',
    ),
    url(
        r'^two_factor/qrcode/$',
        QRGeneratorView.as_view(),
        name='qr',
    ),
    url(
        r'^two_factor/setup/complete/$',
        SetupCompleteView.as_view(),
        name='setup_complete',
    ),
    url(
        r'^two_factor/backup/tokens/$',
        BackupTokensView.as_view(),
        name='backup_tokens',
    ),
    url(
        r'^two_factor/backup/phone/register/$',
        PhoneSetupView.as_view(),
        name='phone_create',
    ),
    url(
        r'^two_factor/backup/phone/unregister/<int:pk>/$',
        PhoneDeleteView.as_view(),
        name='phone_delete',
    ),
]

profile = [
    url(
        r'^two_factor/$',
        ProfileView.as_view(),
        name='profile',
    ),
    url(
        r'^two_factor/disable/$',
        DisableView.as_view(),
        name='disable',
    ),
]

urlpatterns = (core + profile, 'two_factor')
