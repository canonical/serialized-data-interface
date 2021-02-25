from interface_schema import InterfaceSchema
from ops.framework import (
    Object,
)
from ops.charm import CharmBase
import yaml


class ProvideAppInterface(Object):
    SCHEMA = ""

    def __init__(self, charm: CharmBase, relation_name: str, schema_stream: str = None):
        super().__init__(charm, relation_name)
        self.charm = charm
        self.relation_name = relation_name
        # If schema_stream argument is provided overwrite SCHEMA.
        if schema_stream:
            self.SCHEMA = schema_stream
        self.interface_schema = InterfaceSchema(self.SCHEMA)

    def update_relation_data(self, data: dict):
        self.interface_schema.validate(data)

        for relation in self.model.relations[self.relation_name]:
            relation.data[self.charm.app].update({"data": yaml.dump(data)})
