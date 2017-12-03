from django.conf.urls import url
from django.contrib import admin

from .urls import urlpatterns

urlpatterns += [
    url(r'^admin/', admin.site.urls),
]
