from django.conf.urls import url

from two_factor.views import (
    BackupTokensView, DisableView, LoginView, PhoneDeleteView, PhoneSetupView,
    ProfileView, QRGeneratorView, SetupCompleteView, SetupView,
)
from two_factor.forms import (
    U2FDevice,
)
from two_factor.views.core import ManageKeysView

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
    url(
        regex=r'^account/two_factor/manage_keys/$',
        view=ManageKeysView.as_view(),
        name='manage_keys',
    ),
    url(
        regex=r'^account/two_factor/add_u2f_key/$',
        view=SetupView.as_view(
            disabled_methods=(
                'call',
                'sms',
                'yubikey',
                'generator',
            ),
            force=True,
        ),
        name='add_u2f_key'
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

urlpatterns = core + profile
