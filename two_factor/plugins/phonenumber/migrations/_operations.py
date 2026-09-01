"""Shared migration operations for the phonenumber plugin.

The custom ``CreatePhoneDevice`` operation lives here so that both
``0001_initial`` and ``0001_squashed_0001_initial`` can reuse it. Without
this sharing, an installation that migrates the ``two_factor`` app first
and only later enables ``two_factor.plugins.phonenumber`` would end up
recording ``0001_initial`` as applied (state-only) and never create the
``two_factor_phonedevice`` database table.
"""

import django_otp.util
import phonenumber_field.modelfields
from django.conf import settings
from django.db import migrations, models
from django.db.migrations.operations.base import Operation

import two_factor.plugins.phonenumber.models


class CreatePhoneDevice(Operation):
    """Create the ``two_factor_phonedevice`` table if it does not exist.

    The database can be in two different states when this migration is run.

    1. Upgrading from an older version that has the ``two_factor_phonedevice``
       table already created by the ``two_factor`` app. In this case we
       should not create the table.
    2. A fresh install, or an install where ``two_factor.plugins.phonenumber``
       was added to ``INSTALLED_APPS`` after the ``two_factor`` migrations
       have already run. In this case we must create the table.

    Using this custom operation we check whether the table exists before
    creating it.
    """

    reversible = False
    create_model_operation = migrations.CreateModel(
        name='PhoneDevice',
        fields=[
            ('id',
             models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('name', models.CharField(help_text='The human-readable name of this device.', max_length=64)),
            ('confirmed', models.BooleanField(default=True, help_text='Is this device ready for use?')),
            ('throttling_failure_timestamp', models.DateTimeField(
                blank=True, default=None,
                help_text='A timestamp of the last failed verification attempt. '
                          'Null if last attempt succeeded.',
                null=True)),
            ('throttling_failure_count',
             models.PositiveIntegerField(default=0, help_text='Number of successive failed attempts.')),
            ('number', phonenumber_field.modelfields.PhoneNumberField(max_length=128, region=None)),
            ('key', models.CharField(default=django_otp.util.random_hex,
                                     help_text='Hex-encoded secret key',
                                     max_length=40,
                                     validators=[two_factor.plugins.phonenumber.models.key_validator])),
            ('method',
             models.CharField(choices=[('call', 'Phone Call'), ('sms', 'Text Message')], max_length=4,
                              verbose_name='method')),
            ('user', models.ForeignKey(help_text='The user that this device belongs to.',
                                       on_delete=models.deletion.CASCADE,
                                       to=settings.AUTH_USER_MODEL)),
        ],
        options={
            'db_table': 'two_factor_phonedevice',
        },
    )

    def state_forwards(self, app_label, state):
        self.create_model_operation.state_forwards(app_label, state)

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        if "two_factor_phonedevice" not in schema_editor.connection.introspection.table_names():
            # The table doesn't exist. This means we aren't upgrading from a
            # previous version where the two_factor app created the table and
            # need to create the table.
            to_state = from_state.clone()
            self.create_model_operation.state_forwards(app_label, to_state)
            self.create_model_operation.database_forwards(app_label, schema_editor, from_state, to_state)

    def describe(self):
        return "Create PhoneDevice"
