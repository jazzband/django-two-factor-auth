# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django_otp.util
import two_factor.models


class Migration(migrations.Migration):

    dependencies = [
        ('two_factor', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='phonedevice',
            name='key',
            field=models.CharField(default=django_otp.util.random_hex, help_text=b'Hex-encoded secret key', max_length=40, validators=[two_factor.models.key_validator]),
        ),
    ]
