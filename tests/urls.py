from django.conf.urls import patterns, url, include
from django.contrib import admin


admin.autodiscover()

urlpatterns = patterns(
    '',
    url(
        regex=r'^account/logout/$',
        view='django.contrib.auth.views.logout',
        name='logout',
    ),
    url(r'', include('two_factor.urls', 'two_factor')),
    url(r'^admin/', include(admin.site.urls)),
)
