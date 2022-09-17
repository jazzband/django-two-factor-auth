import django_otp.util
from django.db import migrations, models

from two_factor.plugins.phonenumber.models import key_validator


class Migration(migrations.Migration):

    dependencies = [
        ('two_factor', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='phonedevice',
            name='key',
            field=models.CharField(
                default=django_otp.util.random_hex,
                help_text='Hex-encoded secret key',
                max_length=40,
                validators=[key_validator]
            ),
        ),
    ]
