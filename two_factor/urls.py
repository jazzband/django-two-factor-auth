from django.apps.registry import apps
from django.urls import include, path

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

plugin_urlpatterns = []
for app_config in apps.get_app_configs():
    if app_config.name.startswith('two_factor.plugins.'):
        try:
            plugin_urlpatterns.append(
                path(
                    f'account/two_factor/{app_config.url_prefix}/',
                    include(f'{app_config.name}.urls', app_config.label)
                ),
            )
        except AttributeError:
            pass

urlpatterns = (core + profile + plugin_urlpatterns, 'two_factor')
