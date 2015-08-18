# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import two_factor.models


class Migration(migrations.Migration):

    dependencies = [
        ('two_factor', '0002_auto_20150110_0810'),
    ]

    operations = [
        migrations.AlterField(
            model_name='phonedevice',
            name='number',
            field=models.CharField(max_length=16, verbose_name='number', validators=[two_factor.models.phone_number_validator]),
        ),
    ]
