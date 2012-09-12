from django.conf.urls import patterns, url
from two_factor import views

urlpatterns = patterns('two_factor.views',
    url(r'^login/$', 'login', name='login'),
    url(r'^verify/$', 'verify_computer', name='verify'),
    url(r'^verify/enable/$', views.Enable.as_view(), name='enable'),
    url(r'^verify/disable/$', views.Disable.as_view(), name='disable'),
)
