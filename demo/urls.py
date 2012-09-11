from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
from two_factor.views import Enable

admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'demo.views.home', name='home'),
    # url(r'^demo/', include('demo.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    url(r'^accounts/login/$', 'two_factor.views.login'),
    url(r'^accounts/verify/$', 'two_factor.views.verify_computer'),
    url(r'^accounts/profile/$', 'two_factor.views.profile'),
    url(r'^accounts/verify/enable/$', Enable.as_view([])),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)
