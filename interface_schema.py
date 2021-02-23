from jsonschema import validate
import yaml


class InterfaceSchema:
    def __init__(self, schema_file: str):
        with open(schema_file, 'r') as stream:
            self.schema = yaml.safe_load(stream)
    
    def validate(self, data: dict):
        validate(instance=data, schema=self.schema)


