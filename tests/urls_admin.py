from django.contrib import admin
from django.urls import path

from .urls import urlpatterns

urlpatterns += [
    path('admin/', admin.site.urls),
]
