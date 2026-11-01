from django.db import migrations

from ._operations import CreatePhoneDevice


class Migration(migrations.Migration):
    dependencies = [
        ('phonenumber', '0001_initial'),
    ]

    operations = [
        CreatePhoneDevice(),
    ]
