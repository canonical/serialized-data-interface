from operator import attrgetter
from hashlib import md5

import yaml
from interface_schema import InterfaceSchema
from ops.framework import (
    Object,
    StoredState,
    EventBase,
    EventSource,
    ObjectEvents,
)
from ops.charm import CharmBase


class InterfaceDataChanged(EventBase):
    pass


class RequireInterfaceEvents(ObjectEvents):
    data_changed = EventSource(InterfaceDataChanged)


class RequireAppInterface(Object):
    state = StoredState()
    on = RequireInterfaceEvents()
    SCHEMA = ""

    def __init__(self, charm: CharmBase, relation_name: str, schema_stream: str = None):
        super().__init__(charm, relation_name)

        self.charm = charm
        self.relation_name = relation_name
        # If schema_stream argument is provided overwrite SCHEMA.
        if schema_stream:
            self.SCHEMA = schema_stream
        self.interface_schema = InterfaceSchema(self.SCHEMA)
        self.state.set_default(data_hash=None)

        self.framework.observe(
            charm.on[self.relation_name].relation_joined, self._check_data
        )
        self.framework.observe(
            charm.on[self.relation_name].relation_changed, self._check_data
        )

    @property
    def _relations(self):
        return self.model.relations[self.relation_name]

    @property
    def is_available(self) -> bool:
        return len(self.data) > 0

    @property
    def is_created(self) -> bool:
        return len(self._relations) > 0

    @property
    def data(self) -> list:
        data = []
        for relation in sorted(self._relations, key=attrgetter("id")):
            if not relation.app:
                continue
            raw_relation_data = relation.data[relation.app].get("data")

            if not raw_relation_data:
                continue

            relation_data = yaml.safe_load(raw_relation_data)

            self.interface_schema.validate(relation_data)
            data.append(relation_data)
        return data

    @property
    def _data_hash(self) -> str:
        return md5(str(self.data).encode("utf8")).hexdigest()

    def _check_data(self, event: EventBase):
        if self.is_available and self.state.data_hash != self._data_hash:
            self.state.data_hash = self._data_hash
            self.on.data_changed.emit()
