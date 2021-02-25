from jsonschema import validate
import yaml


class InterfaceSchema:
    def __init__(self, schema: str):
        self.schema = {
            "type": "object",
            "properties": yaml.safe_load(schema),
        }

    def validate(self, data: dict):
        validate(instance=data, schema=self.schema)
