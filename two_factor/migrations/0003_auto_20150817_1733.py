# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging

from django.db import models, migrations
from django.contrib.auth import get_user_model

import phonenumbers
import two_factor.models

logger = logging.getLogger(__name__)


def migrate_phone_numbers(apps, schema_editor):
    username_field = get_user_model().USERNAME_FIELD
    PhoneDevice = apps.get_model("two_factor", "PhoneDevice")
    for device in PhoneDevice.objects.all():
        username = getattr(device.user, username_field)
        try:
            number = phonenumbers.parse(device.number)
            if not phonenumbers.is_valid_number(number):
                logger.info("User '%s' has an invalid phone number '%s'." % (username, device.number))
            device.number = phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)
            device.save()
        except phonenumbers.NumberParseException as e:
            # Do not modify/delete the device, as it worked before. However this might result in issues elsewhere,
            # so do log a warning.
            logger.warning("User '%s' has an invalid phone number '%s': %s. Please resolve this issue, "
                           "as it might result in errors." % (username, device.number, e))


class Migration(migrations.Migration):

    dependencies = [
        ('two_factor', '0002_auto_20150110_0810'),
    ]

    operations = [
        migrations.RunPython(migrate_phone_numbers, reverse_code=lambda apps, schema_editor: None),
        migrations.AlterField(
            model_name='phonedevice',
            name='number',
            field=two_factor.models.PhoneNumberField(max_length=16, verbose_name='number'),
        ),
    ]
