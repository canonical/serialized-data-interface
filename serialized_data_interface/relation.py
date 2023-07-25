# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.
"""Base class for libraries which wrap a relation endpoint with a Python API.

This provides the base for implementing relation libraries which use SDI
for data validation and de/serialization but provide a Python API on top
of that for ease of use.
"""
import logging
from functools import cached_property
from pathlib import Path
from typing import Dict, Optional, Union

import yaml
from ops.charm import CharmBase
from ops.framework import Object
from ops.model import (
    ActiveStatus,
    Application,
    BlockedStatus,
    Relation,
    Unit,
    WaitingStatus,
)

from . import errors, utils
from .events import EndpointWrapperEvents
from .sdi import SerializedDataInterface
from .shims import cache

log = logging.getLogger(__name__)


class EndpointWrapper(Object):
    """Base class for schema-based operator relation libraries.

    Class Attributes:
        ROLE: Relation role which this class implements.
        Must be set by subclass.

        INTERFACE: Interface protocol name.
        Must be set by subclass.

        SCHEMA: A pathlib.Path pointing to the schemas YAML file,
        or schemas data structure. Must be set by subclass.

        LIMIT: Limit, if any, for relation endpoint connections.

    Attributes:
        auto_data: Data to be automatically passed to `wrap()` as
        soon as possible for any relation. Must work with any supported
        version which could be negotiated.

        ignored_fields: Set of field names from remote relation data which
        should be ignored as not part of the schema. The default is the supported
        versions field, and the fields automatically populated by Juju.
    """

    ROLE: str
    INTERFACE: str
    SCHEMA: Union[str, dict]
    LIMIT: Union[int, None] = None

    on = EndpointWrapperEvents()

    def __init__(self, charm: CharmBase, endpoint: Optional[str] = None):
        """Constructor for EndpointWrapper.

        Args:
            charm: The charm that is instantiating the library.
            endpoint: The name of the relation endpoint to bind to
                (defaults to the INTERFACE, with any underscores
                changed to dashes).
        """
        if endpoint is None:
            endpoint = self._default_endpoint
        super().__init__(charm, f"relation-{endpoint}")
        self.charm = charm
        self.endpoint = endpoint
        self.auto_data = getattr(self, "auto_data", None)
        self.ignored_fields = getattr(
            self,
            "ignored_fields",
            {
                utils.VERSION_KEY,
                "egress-subnets",
                "ingress-address",
                "private-address",
            },
        )

        schemas = self._load_schemas()
        self._sdi = SerializedDataInterface(
            charm,
            endpoint,
            schemas,
            set(schemas.keys()),
            self.ROLE,
            self.ignored_fields,
        )

        self._validate_relation_meta()

        rel_events = charm.on[endpoint]
        self.framework.observe(rel_events.relation_created, self._handle_relation)
        self.framework.observe(rel_events.relation_changed, self._handle_relation)
        self.framework.observe(rel_events.relation_broken, self._handle_relation_broken)
        self.framework.observe(charm.on.leader_elected, self._handle_upgrade_or_leader)
        self.framework.observe(charm.on.upgrade_charm, self._handle_upgrade_or_leader)

    @property
    def _default_endpoint(self):
        return self.INTERFACE.replace("_", "-")

    @property
    def app(self):
        """Shortcut to self.charm.app."""
        return self.charm.app

    @property
    def unit(self):
        """Shortcut to self.charm.unit."""
        return self.charm.unit

    def _load_schemas(self):
        if isinstance(self.SCHEMA, dict):
            return self.SCHEMA
        elif isinstance(self.SCHEMA, Path):
            try:
                return yaml.safe_load(self.SCHEMA.read_text())
            except (OSError, yaml.YAMLError) as e:
                raise errors.SchemaParseError(str(e)) from e
        else:
            raise errors.SchemaError(
                f"SCHEMA type must be Path or dict, not {type(self.SCHEMA)}"
            )

    def _validate_relation_meta(self):
        """Validate that the relation is setup properly in the metadata."""
        # This should really be done as a build-time hook, if that were possible.
        cls_name = type(self).__name__
        assert (
            self.endpoint in self.charm.meta.relations
        ), f"Relation {self.endpoint} not found"
        rel_meta = self.charm.meta.relations[self.endpoint]
        assert (
            self.ROLE == rel_meta.role.name
        ), f"{cls_name} must be used on a '{self.ROLE}' relation"
        assert (
            rel_meta.interface_name == self.INTERFACE
        ), f"{cls_name} must be used on an '{self.INTERFACE}' relation endpoint"
        if self.LIMIT is not None:
            assert (
                rel_meta.limit == 1
            ), f"{cls_name} must be used on a 'limit: {self.LIMIT}' relation endpoint"

    @property
    def versions(self):
        """Set of supported versions."""
        return self._sdi.versions

    @cached_property
    def relations(self):
        """The list of Relation instances associated with this endpoint."""
        return list(self.charm.model.relations[self.endpoint])

    @cache
    def get_status(self, relation: Relation):
        """Get the suggested status for the given Relation."""
        if self.is_failed(relation):
            return BlockedStatus(f"Error handling relation: {relation.name}")
        elif not self.is_available(relation):
            if relation.units:
                # If we have remote units but still no version, then there's
                # probably something wrong and we should be blocked.
                return BlockedStatus(f"Missing relation versions: {relation.name}")
            else:
                # Otherwise, we might just not have seen the versions yet.
                return WaitingStatus(f"Waiting on relation: {relation.name}")
        elif not self.is_ready(relation):
            return WaitingStatus(f"Waiting on relation: {relation.name}")
        return ActiveStatus()

    @cache
    def is_available(self, relation: Optional[Relation] = None):
        """Checks whether the given relation, or any relation if not specified, is available.

        A given relation is available if the version negotation has succeeded.
        """
        if relation is None:
            return any(self.is_available(relation) for relation in self.relations)
        if relation.app.name == "":  # type: ignore
            # Juju doesn't provide JUJU_REMOTE_APP during relation-broken
            # hooks. See https://github.com/canonical/operator/issues/693
            return False
        try:
            self._sdi.get_version(relation)
        except errors.RelationException:
            return False
        else:
            return True

    @cache
    def is_ready(self, relation: Optional[Relation] = None):
        """Checks whether the given relation, or any relation if not specified, is ready.

        A given relation is ready if the remote side has sent valid data.
        """
        if relation is None:
            return any(self.is_ready(relation) for relation in self.relations)
        if relation.app.name == "":  # type: ignore
            # Juju doesn't provide JUJU_REMOTE_APP during relation-broken
            # hooks. See https://github.com/canonical/operator/issues/693
            return False
        try:
            data = self.unwrap(relation)
        except errors.RelationException:
            return False
        else:
            return any(
                data[entity] for entity in data if entity not in (self.app, self.unit)
            )

    @cache
    def is_failed(self, relation: Optional[Relation] = None):
        """Checks whether the given relation, or any relation if not specified, has an error."""
        if relation is None:
            return any(self.is_failed(relation) for relation in self.relations)
        if relation.app.name == "":  # type: ignore
            # Juju doesn't provide JUJU_REMOTE_APP during relation-broken
            # hooks. See https://github.com/canonical/operator/issues/693
            return False
        try:
            self.unwrap(relation)
        except errors.RelationError as e:
            log.exception(f"Error handling relation: {e}")
            return True
        except errors.UnversionedRelation:
            if relation.units:
                # If we have remote units but still no version, then there's
                # probably something wrong.
                return True
            else:
                return False
        except errors.RelationException:
            return False
        else:
            return False

    def _handle_relation(self, event):
        self._send_versions(event.relation)
        self._send_auto_data(event.relation)
        if self.is_ready(event.relation):
            self.on.ready.emit(event.relation)
        elif self.is_available(event.relation):
            self.on.available.emit(event.relation)
        elif self.is_failed(event.relation):
            self.on.failed.emit(event.relation)

    def _handle_relation_broken(self, event):
        self.on.broken.emit(event.relation)

    def _handle_upgrade_or_leader(self, event):
        for relation in self.relations:
            self._send_versions(relation)
            self._send_auto_data(relation)

    def _send_versions(self, relation):
        self._sdi.send_versions(relation)

    def _send_auto_data(self, relation):
        if self.auto_data and self.is_available(relation):
            self.wrap(relation, self.auto_data)

    def unwrap(self, relation: Relation):
        """Deserialize and validate the data from the relation.

        Deserialize and validate all available data from the relation. The returned
        dictionary has the same keys as `relation.data` (i.e., the local and remote
        Applications and Units).

        If the current unit is not the leader, the data for the current Application
        will always be an empty dict.  See: https://bugs.launchpad.net/juju/+bug/1958530

        Can raise:
            * IncompatibleVersionsError
            * RelationParseError
            * RelationDataError
        """
        return self._sdi.unwrap(relation)

    def wrap(self, relation: Relation, data: Dict[Union[Application, Unit], dict]):
        """Validate and serialize the data and put it into the relation.

        Validates that the local app and / or unit data is valid against the schema,
        and if so, serializes it and returns it.

        Can raise:
            * ModelError (when setting app data and not leader)
            * UnversionedRelation (when relation not available)
            * RelationParseError (when relation not available)
            * IncompatibleVersionsError (when relation not available)
            * RelationDataError (when given data is invalid)

        Example:
                self.wrap(relation, {self.app: {"foo": "bar"}})
        """
        self._sdi.wrap(relation, data)
