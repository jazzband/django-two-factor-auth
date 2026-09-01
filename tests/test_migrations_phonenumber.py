"""Regression tests for the phonenumber plugin migrations.

The phonenumber app's first migration (``0001_initial``) historically used
``SeparateDatabaseAndState`` with only ``state_operations``. That meant
installing the ``phonenumber`` plugin *after* the ``two_factor`` migrations
had already run would record the state of ``PhoneDevice`` but never create
the underlying ``two_factor_phonedevice`` table. See issue #800.

The fix introduces a shared ``CreatePhoneDevice`` operation that performs
the actual ``CreateModel`` whenever the table is missing, and uses it from
both ``0001_initial`` and ``0001_squashed_0001_initial``.
"""

from django.apps import apps
from django.core.management import call_command
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder
from django.test import TransactionTestCase


PHONE_DEVICE_TABLE = "two_factor_phonedevice"


def _has_table(table_name):
    return table_name in connection.introspection.table_names()


def _drop_phone_device_table():
    """Drop the phonenumber table via the schema editor if it exists."""
    model = apps.get_model("phonenumber", "PhoneDevice")
    with connection.schema_editor() as editor:
        if PHONE_DEVICE_TABLE in connection.introspection.table_names():
            editor.delete_model(model)


def _unrecord_migration(app, name):
    """Remove a single ``(app, name)`` entry from django_migrations."""
    recorder = MigrationRecorder(connection)
    recorder.record_unapplied(app, name)


class PhonenumberInitialMigrationCreatesTableTest(TransactionTestCase):
    """End-to-end regression test for issue #800."""

    def test_initial_migration_creates_table_when_missing(self):
        """``0001_initial`` must create the table if it is missing.

        Simulates the scenario from the bug report: ``two_factor`` was
        migrated first, then ``two_factor.plugins.phonenumber`` was added
        to ``INSTALLED_APPS`` and migrated afterwards. Before the fix,
        ``0001_initial`` would record the state but leave the database
        without the ``two_factor_phonedevice`` table.
        """
        # The test runner already applied phonenumber migrations, including
        # 0001_initial, so the table currently exists.
        self.assertTrue(_has_table(PHONE_DEVICE_TABLE))

        # Forget that 0001_initial was applied and drop the table to
        # simulate the bug scenario, then re-run the migration.
        _unrecord_migration("phonenumber", "0001_initial")
        _drop_phone_device_table()
        self.assertFalse(_has_table(PHONE_DEVICE_TABLE))

        call_command("migrate", "phonenumber", "0001_initial", verbosity=0)

        self.assertTrue(
            _has_table(PHONE_DEVICE_TABLE),
            "0001_initial must create two_factor_phonedevice",
        )


class CreatePhoneDeviceOperationTest(TransactionTestCase):
    """Direct unit tests for the shared ``CreatePhoneDevice`` operation."""

    def test_noop_when_table_already_exists(self):
        """The operation must be a safe no-op when the table exists.

        Mirrors the upgrade path described in the operation's docstring:
        a database that already has ``two_factor_phonedevice`` (because
        the original ``two_factor`` app created it before the squashed
        migration existed) must not be re-created.
        """
        self.assertTrue(_has_table(PHONE_DEVICE_TABLE))
        # Running the migration again must succeed without raising.
        call_command("migrate", "phonenumber", "0001_initial", verbosity=0)
        self.assertTrue(_has_table(PHONE_DEVICE_TABLE))
