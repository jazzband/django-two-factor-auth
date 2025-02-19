from django.urls import path

from .views import PhoneDeleteView, PhoneSetupView

urlpatterns = [
    path(
        'register/',
        PhoneSetupView.as_view(),
        name='phone_create',
    ),
    path(
        'unregister/<int:pk>/',
        PhoneDeleteView.as_view(),
        name='phone_delete',
    ),
]
