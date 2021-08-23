from django.urls import path

from two_factor.views import (
    BackupTokensView, DisableView, LoginView, PhoneDeleteView, PhoneSetupView,
    ProfileView, QRGeneratorView, SetupCompleteView, SetupView,
)

core = [
    path(
        'two_factor/login/',
        LoginView.as_view(),
        name='login',
    ),
    path(
        'two_factor/setup/',
        SetupView.as_view(),
        name='setup',
    ),
    path(
        'two_factor/qrcode/',
        QRGeneratorView.as_view(),
        name='qr',
    ),
    path(
        'two_factor/setup/complete/',
        SetupCompleteView.as_view(),
        name='setup_complete',
    ),
    path(
        'two_factor/backup/tokens/',
        BackupTokensView.as_view(),
        name='backup_tokens',
    ),
    path(
        'two_factor/backup/phone/register/',
        PhoneSetupView.as_view(),
        name='phone_create',
    ),
    path(
        'two_factor/backup/phone/unregister/<int:pk>',
        PhoneDeleteView.as_view(),
        name='phone_delete',
    ),
]

profile = [
    path(
        'two_factor/',
        ProfileView.as_view(),
        name='profile',
    ),
    path(
        'two_factor/disable/',
        DisableView.as_view(),
        name='disable',
    ),
]

urlpatterns = (core + profile, 'two_factor')
