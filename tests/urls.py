from django.conf.urls import patterns, url, include
from django.contrib import admin

from two_factor.views import LoginView


admin.autodiscover()

urlpatterns = patterns(
    '',
    url(
        regex=r'^account/logout/$',
        view='django.contrib.auth.views.logout',
        name='logout',
    ),
    url(
        regex=r'account/custom-login/$',
        view=LoginView.as_view(redirect_field_name='next_page'),
        name='custom-login',
    ),
    url(r'', include('two_factor.urls', 'two_factor')),
    url(r'^admin/', include(admin.site.urls)),
)
