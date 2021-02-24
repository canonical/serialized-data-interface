from interface_schema import InterfaceSchema
from ops.framework import (
    Object,
)
from ops.charm import CharmBase
import yaml


class ProvideAppInterface(Object):
    def __init__(
        self, charm: CharmBase, relation_name: str, interface_schema: str
    ):
        super().__init__(charm, relation_name)
        self.charm = charm
        self.relation_name = relation_name
        self.interface_schema = InterfaceSchema(interface_schema)

    def update_relation_data(self, data: dict):
        self.interface_schema.validate(data)

        for relation in self.model.relations[self.relation_name]:
            relation.data[self.charm.app].update({"data": yaml.dump(data)})
