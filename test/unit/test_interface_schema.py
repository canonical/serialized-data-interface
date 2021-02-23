from unittest import TestCase
from interface_schema import InterfaceSchema
from jsonschema.exceptions import ValidationError


class InterfaceSchemaTestCase(TestCase):
    def test_success_validate_schema(self):
        test_schema = InterfaceSchema("test/unit/test_schema.yaml")
        data = {
            "service": "my-service",
            "port": 4242,
            "access-key": "my-access-key",
            "secret-key": "my-secret-key",
        }
        test_schema.validate(data)
        pass

    def test_failed_validate_schema(self):
        with self.assertRaises(ValidationError):
            test_schema = InterfaceSchema("test/unit/test_schema.yaml")
            data = {
                "service": "my-service",
                "port": "4242",
                "access-key": "my-access-key",
                "secret-key": "my-secret-key",
            }
            test_schema.validate(data)
