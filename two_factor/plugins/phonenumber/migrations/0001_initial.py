from django.conf import settings
from django.db import migrations

from ._operations import CreatePhoneDevice


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('two_factor', '0008_delete_phonedevice'),
    ]

    operations = [
        CreatePhoneDevice(),
    ]
