from django.test import TestCase

from two_factor.plugins.registry import (
    GeneratorMethod, MethodBase, MethodNotFoundError, registry,
)


class FakeMethod(MethodBase):
    code = 'fake-method'


class RegistryTest(TestCase):
    def setUp(self) -> None:
        self.old_methods = list(registry._methods)
        return super().setUp()

    def tearDown(self) -> None:
        registry._methods = self.old_methods
        return super().tearDown()

    def test_register(self):
        previous_length = len(registry._methods)
        expected_length = previous_length + 1

        registry.register(FakeMethod())
        self.assertEqual(len(registry._methods), expected_length)

    def test_register_twice(self):
        previous_length = len(registry._methods)
        expected_length = previous_length

        registry.register(GeneratorMethod())
        self.assertEqual(len(registry._methods), expected_length)

    def test_unregister(self):
        previous_length = len(registry._methods)
        expected_length = previous_length - 1

        registry.unregister('generator')
        self.assertEqual(len(registry._methods), expected_length)

    def test_unregister_non_registered(self):
        previous_length = len(registry._methods)
        expected_length = previous_length

        registry.unregister('fake-method')
        self.assertEqual(len(registry._methods), expected_length)

    def test_unknown_method(self):
        with self.assertRaises(MethodNotFoundError):
            registry.get_method("not-existing-method")
