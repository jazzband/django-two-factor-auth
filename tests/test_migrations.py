from io import StringIO

from django.core.management import call_command
from django.db import connection
from django.test import TransactionTestCase


class PhonenumberMigrationTests(TransactionTestCase):
    def test_phonenumber_migration_reversible(self):
        out = StringIO()
        call_command("migrate", "phonenumber", "zero", verbosity=0, stdout=out)
        self.assertNotIn("two_factor_phonedevice", connection.introspection.table_names())

        call_command("migrate", "phonenumber", verbosity=0, stdout=out)
        self.assertIn("two_factor_phonedevice", connection.introspection.table_names())
