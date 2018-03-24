from django.contrib import admin

from .models import EmailDevice


@admin.register(EmailDevice)
class EmailDeviceAdmin(admin.ModelAdmin):
    """
    :class:`~django.contrib.admin.ModelAdmin` for
    :class:`~two_factor.plugins.email.models.EmailDevice`.
    """
    raw_id_fields = ('user',)
