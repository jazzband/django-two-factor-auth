from django.conf.urls import url

from two_factor.views import (
    BackupTokensView, DisableView, LoginView, PhoneDeleteView, PhoneSetupView,
    ProfileView, QRGeneratorView, SetupCompleteView, SetupView,
)

core = [
    url(
        regex=r'^account/login/$',
        view=LoginView.as_view(),
        name='login',
    ),
    url(
        regex=r'^account/two_factor/setup/$',
        view=SetupView.as_view(),
        name='setup',
    ),
    url(
        regex=r'^account/two_factor/qrcode/$',
        view=QRGeneratorView.as_view(),
        name='qr',
    ),
    url(
        regex=r'^account/two_factor/setup/complete/$',
        view=SetupCompleteView.as_view(),
        name='setup_complete',
    ),
    url(
        regex=r'^account/two_factor/backup/tokens/$',
        view=BackupTokensView.as_view(),
        name='backup_tokens',
    ),
    url(
        regex=r'^account/two_factor/backup/phone/register/$',
        view=PhoneSetupView.as_view(),
        name='phone_create',
    ),
    url(
        regex=r'^account/two_factor/backup/phone/unregister/(?P<pk>\d+)/$',
        view=PhoneDeleteView.as_view(),
        name='phone_delete',
    ),
]

profile = [
    url(
        regex=r'^account/two_factor/$',
        view=ProfileView.as_view(),
        name='profile',
    ),
    url(
        regex=r'^account/two_factor/disable/$',
        view=DisableView.as_view(),
        name='disable',
    ),
]

urlpatterns = (core + profile, 'two_factor')
