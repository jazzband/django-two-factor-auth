from django.urls import path

from two_factor.plugins.phonenumber.views import (
    PhoneDeleteView, PhoneSetupView,
)
from two_factor.views import (
    BackupTokensView, DisableView, LoginView, ProfileView, QRGeneratorView,
    SetupCompleteView, SetupView,
)

core = [
    path(
        'account/login/',
        LoginView.as_view(),
        name='login',
    ),
    path(
        'account/two_factor/setup/',
        SetupView.as_view(),
        name='setup',
    ),
    path(
        'account/two_factor/qrcode/',
        QRGeneratorView.as_view(),
        name='qr',
    ),
    path(
        'account/two_factor/setup/complete/',
        SetupCompleteView.as_view(),
        name='setup_complete',
    ),
    path(
        'account/two_factor/backup/tokens/',
        BackupTokensView.as_view(),
        name='backup_tokens',
    ),
    path(
        'account/two_factor/backup/phone/register/',
        PhoneSetupView.as_view(),
        name='phone_create',
    ),
    path(
        'account/two_factor/backup/phone/unregister/<int:pk>/',
        PhoneDeleteView.as_view(),
        name='phone_delete',
    ),
]

profile = [
    path(
        'account/two_factor/',
        ProfileView.as_view(),
        name='profile',
    ),
    path(
        'account/two_factor/disable/',
        DisableView.as_view(),
        name='disable',
    ),
]

urlpatterns = (core + profile, 'two_factor')
