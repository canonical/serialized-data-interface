from unittest import TestCase
from interface_schema import InterfaceSchema
from jsonschema.exceptions import ValidationError


class InterfaceSchemaTestCase(TestCase):
    def test_success_validate_schema(self):
        with open("test/unit/test_schema.yaml", "r") as stream:
            test_schema = InterfaceSchema(stream)

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
            with open("test/unit/test_schema.yaml", "r") as stream:
                test_schema = InterfaceSchema(stream)
            data = {
                "service": "my-service",
                "port": "4242",
                "access-key": "my-access-key",
                "secret-key": "my-secret-key",
            }
            test_schema.validate(data)
