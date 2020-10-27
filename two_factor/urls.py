from django.conf.urls import url

from two_factor.views import (
    BackupTokensView, DisableView, LoginView, PhoneDeleteView, PhoneSetupView,
    ProfileView, QRGeneratorView, SetupCompleteView, SetupView,
)

core = [
    url(
        r'^account/login/$',
        LoginView.as_view(),
        name='login',
    ),
    url(
        r'^account/two_factor/setup/$',
        SetupView.as_view(),
        name='setup',
    ),
    url(
        r'^account/two_factor/qrcode/$',
        QRGeneratorView.as_view(),
        name='qr',
    ),
    url(
        r'^account/two_factor/setup/complete/$',
        SetupCompleteView.as_view(),
        name='setup_complete',
    ),
    url(
        r'^account/two_factor/backup/tokens/$',
        BackupTokensView.as_view(),
        name='backup_tokens',
    ),
    url(
        r'^account/two_factor/backup/phone/register/$',
        PhoneSetupView.as_view(),
        name='phone_create',
    ),
    url(
        r'^account/two_factor/backup/phone/unregister/<int:pk>/$',
        PhoneDeleteView.as_view(),
        name='phone_delete',
    ),
]

profile = [
    url(
        r'^account/two_factor/$',
        ProfileView.as_view(),
        name='profile',
    ),
    url(
        r'^account/two_factor/disable/$',
        DisableView.as_view(),
        name='disable',
    ),
]

urlpatterns = (core + profile, 'two_factor')
