# Copyright 2023 Canonical Ltd.
from functools import cached_property
from typing import Dict, Optional, Set, Tuple, Union

import jsonschema
import yaml
from ops.charm import CharmBase
from ops.model import Application, Relation, RelationDataContent, Unit

from . import errors, utils


class SerializedDataInterface:
    """Represents a schema-defined interface between two charms.

    The schema should match the JSON Schema specification, though
    should be written in YAML.
    """

    def __init__(
        self,
        charm: CharmBase,
        endpoint: str,
        schemas: dict,
        versions: Set[Union[int, str]],
        role: str,
        ignored_fields: Optional[Set[str]] = None,
    ):
        """Initialize the SDI instance.

        Args:
            charm: The charm that this is being used with.
            endpoint: The name of the relation endpoint to use.
            schemas: The mapping of versions to role-entity-schema mappings.
            versions: Set of supported versions.
            role: The role for the local side of the relation.
            ignored_fields: Optional set of fields to ignore when validating and deserializing.
        """
        self.charm = charm
        self.endpoint = endpoint
        self.schemas = schemas
        self.versions = versions
        if role not in utils.ROLE_MAP:
            raise errors.InvalidRoleError(role)
        self.role, self.remote_role = utils.ROLE_MAP[role]
        self.ignored_fields = ignored_fields or set()
        self._convert_implicit_schemas()
        self._validate_schemas()

    def _convert_implicit_schemas(self):
        # Convert older schemas which are implicitly app-only to be explicit.
        for version_schemas in self.schemas.values():
            for role, role_schema in version_schemas.items():
                if role not in utils.ROLE_MAP:
                    # Ignore non-role sections (e.g., the "flat" flag).
                    continue
                if not {"app", "unit"}.issuperset(role_schema.keys()):
                    version_schemas[role] = {"app": role_schema}

    def _validate_schemas(self):
        self._parse_versions(self.schemas.keys())  # verify versions can be parsed
        for version, schema in self.schemas.items():
            try:
                jsonschema.validators.validator_for(schema).check_schema(schema)
            except jsonschema.SchemaError as e:
                raise errors.InvalidSchemaError(version, str(e)) from e

    @property
    def app(self):
        """Shortcut to self.charm.app."""
        return self.charm.app

    @property
    def unit(self):
        """Shortcut to self.charm.unit."""
        return self.charm.unit

    def _parse_versions(self, versions):
        parsed = {}
        for version in versions:
            if isinstance(version, int):
                parsed[version] = version
            elif isinstance(version, str) and version.startswith("v"):
                try:
                    parsed[int(version[1:])] = version
                except ValueError as e:
                    raise errors.InvalidSchemaVersionError(version) from e
            else:
                raise errors.InvalidSchemaVersionError(version)
        return parsed

    @cached_property
    def max_version(self):
        """The maximum version supported by this instance."""
        parsed = self._parse_version(self.versions)
        max_version = max(parsed.keys())
        return parsed[max_version]

    def get_version(self, relation: Relation):
        """Get the maximum compatible version for a given Relation.

        Can raise:
            * UnversionedRelation
            * RelationParseError
            * IncompatibleVersionsError
        """
        local_versions = self.versions
        local_versions_parsed = self._parse_versions(local_versions)
        remote_versions_raw = relation.data[relation.app].get(utils.VERSION_KEY)  # type: ignore
        if not remote_versions_raw:
            raise errors.UnversionedRelation(relation)
        try:
            if not isinstance(remote_versions_raw, str):
                raise TypeError(f"should be str, not {type(remote_versions_raw)}")
            remote_versions = set(yaml.safe_load(remote_versions_raw))
            remote_versions_parsed = self._parse_versions(remote_versions)
        except (TypeError, yaml.YAMLError) as e:
            raise errors.RelationParseError(
                relation,
                relation.app,  # type: ignore
                "_supported_versions",
            ) from e
        compatible_versions = (
            local_versions_parsed.keys() & remote_versions_parsed.keys()
        )
        if not compatible_versions:
            raise errors.IncompatibleVersionsError(
                relation, local_versions, remote_versions
            )
        return local_versions_parsed[max(compatible_versions)]

    def _get_entity_schema(
        self, version: Union[int, str], entity: Union[Application, Unit]
    ):
        if entity is self.app:
            return self.schemas[version].get(self.role, {}).get("app", {})
        elif entity is self.unit:
            return self.schemas[version].get(self.role, {}).get("unit", {})
        elif isinstance(entity, Application):
            return self.schemas[version].get(self.remote_role, {}).get("app", {})
        elif isinstance(entity, Unit):
            return self.schemas[version].get(self.remote_role, {}).get("unit", {})

    def send_versions(self, relation: Relation):
        """Send the list of supported versions to the related app.

        If not the leader, does nothing.
        """
        if self.unit.is_leader():
            serialized = yaml.safe_dump(list(self.versions))
            relation.data[self.app][utils.VERSION_KEY] = serialized

    def __repr__(self):
        return (
            f"SerializedDataInterface(charm={self.charm}, endpoint={self.endpoint}, "
            f"schemas={self.schemas}, versions={self.versions}, role={self.role})"
        )

    @property
    def _relations(self):
        return [rel for rel in self.charm.model.relations[self.endpoint] if rel.app]

    def get_data(self) -> Dict[Tuple[Relation, Application], Dict]:
        """Get unwrapped data for all relations.

        If any relation has an error or is unversioned, it will be surfaced immediately.

        Returns a mapping of (relation, relation.app) tuples to the unwrapped data for that app.
        """
        data = {}
        for relation in self._relations:
            rel_data = self.unwrap(relation)
            if rel_data[relation.app]:
                data[(relation, relation.app)] = rel_data[relation.app]
            if self.unit.is_leader() and rel_data[self.app]:
                data[(relation, self.app)] = rel_data[self.app]
        return data

    def send_data(self, data: dict, app_name: Optional[str] = None):
        """Send data to related app(s).

        If `app_name` is given, the data will only be sent to relations with that remote
        application. Otherwise, it will be sent to all relations. Note that this means that
        either the data given has to be compatible with any established relation versions.
        """
        if not app_name:
            # Use all relations since we don't have an app name to filter by.
            relations = self._relations
            # Verify that we don't need an app name due to only a single version being in use.
            versions = {self.get_version(relation) for relation in self._relations}
            if len(versions) > 1:
                raise errors.AppNameOmittedError(self.endpoint, list(versions))
        else:
            # Filter the set of relations by app name.
            relations = [
                relation
                for relation in self._relations
                if relation.app.name == app_name
            ]
            # Verify that the app name given was a valid one and that we have relations to send to.
            if not relations:
                raise errors.InvalidAppNameError(self.endpoint, app_name)
        data = {self.app: data}
        for relation in relations:
            self.wrap(relation, data)

    def _deserialize_flat(
        self,
        relation: Relation,
        entity: Union[Application, Unit],
        data: RelationDataContent,
    ):
        # Deserialize "flat" schema data, where each field is serliazed directly
        # into the relation data bucket, rather than under a nested "data" field.
        deserialized = {}
        for key, value in data.items():
            if key in self.ignored_fields:
                continue
            try:
                deserialized[key] = yaml.safe_load(value)
            except yaml.YAMLError as e:
                raise errors.RelationParseError(relation, entity, key) from e
        return deserialized

    def _deserialize_nested(
        self,
        relation: Relation,
        entity: Union[Application, Unit],
        data: RelationDataContent,
    ):
        # Deserialize "nested" schema data, where all data is serialized under
        # a single "data" key.
        try:
            return yaml.safe_load(data.get("data", "{}"))
        except yaml.YAMLError as e:
            raise errors.RelationParseError(relation, entity, "data") from e

    def _serialize_flat(self, bucket: RelationDataContent, data: dict):
        for field, value in data.items():
            bucket[field] = yaml.safe_dump(value)
        for removed_field in set.difference(
            set(bucket.keys()),
            set(data.keys()),
            self.ignored_fields,
        ):
            del bucket[field]

    def _serialize_nested(self, bucket: RelationDataContent, data: dict):
        bucket["data"] = yaml.safe_dump(data)

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
        if not relation.app or not relation.app.name:
            # Handle edge case where remote app name can be missing.
            return {relation.app: {}, self.app: {}, self.unit: {}}
        version = self.get_version(relation)
        unwrapped: dict = {}
        for entity, data in relation.data.items():
            if entity is self.app and not self.unit.is_leader():
                unwrapped[entity] = {}
                continue
            entity_schema = self._get_entity_schema(version, entity)
            if self.schemas[version].get("flat", False):
                deserialized = self._deserialize_flat(relation, entity, data)
            else:
                deserialized = self._deserialize_nested(relation, entity, data)
            if deserialized:
                if not entity_schema:
                    role = (
                        self.role
                        if entity in {self.app, self.unit}
                        else self.remote_role
                    )
                    raise errors.MissingSchemaError(relation, role, entity)
                try:
                    jsonschema.validate(instance=deserialized, schema=entity_schema)
                except jsonschema.ValidationError as e:
                    raise errors.RelationDataError(relation, entity) from e
            unwrapped[entity] = deserialized
        return unwrapped

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
        if data.get(self.app) and not self.unit.is_leader():
            raise errors.RelationPermissionError(relation, self.app)
        old_data = self.unwrap(relation)
        version = self.get_version(relation)
        for entity in data.keys():
            if not data[entity]:
                continue
            if entity not in (self.app, self.unit):
                if data[entity] != old_data.get(entity):
                    raise errors.RelationPermissionError(relation, entity)
                continue
            entity_schema = self._get_entity_schema(version, entity)
            if not entity_schema:
                raise errors.MissingSchemaError(relation, self.role, entity)
            try:
                jsonschema.validate(instance=data[entity], schema=entity_schema)
            except jsonschema.ValidationError as e:
                raise errors.RelationDataError(relation, entity) from e
            else:
                bucket = relation.data[entity]
                if self.schemas[version].get("flat", False):
                    self._serialize_flat(bucket, data[entity])
                else:
                    self._serialize_nested(bucket, data[entity])


def get_interfaces(charm) -> Dict[str, Optional[SerializedDataInterface]]:
    """Reads metadata.yaml to retrieve schema-checked interface objects.

    The returned dictionary will always contain keys for each interface that
    defines a schema, but the associated values may be None, if no relations
    have been made yet on that interface. This is because instantiating the
    SerializedDataInterface class requires agreeing on a schema version by
    both sides of the relation.
    """
    # Can't just use charm.meta.relations because it doesn't preserve unknown
    # fields (i.e., "schema" and "versions").
    with open("metadata.yaml") as f:
        metadata = yaml.safe_load(f)

    return {
        endpoint: get_interface(charm, endpoint)
        for endpoint, endpoint_info in charm.meta.relations.items()
        if "schema" in metadata[endpoint_info.role.name][endpoint]
    }


def get_interface(charm, endpoint: str) -> Optional[SerializedDataInterface]:
    """Reads metadata.yaml to retrieve schema-checked interface object.

    If the interface has established relations, send_versions will be automatically called for
    each of them.  If the interface has no established relations, will return None instead.
    """
    if endpoint not in charm.meta.relations:
        raise errors.UnknownEndpointError(endpoint)

    # Can't just use charm.meta.relations because it doesn't preserve unknown
    # fields (i.e., "schema" and "versions").
    with open("metadata.yaml") as f:
        metadata = yaml.safe_load(f)

    relations = {**metadata.get("provides", {}), **metadata.get("requires", {})}

    interface = relations[endpoint]
    schema = utils.get_schema(interface["schema"])

    instance = SerializedDataInterface(
        charm,
        endpoint,
        schema,
        set(interface["versions"]),
        charm.meta.relations[endpoint].role.name,
    )
    if instance._relations:
        for relation in charm.model.relations[endpoint]:
            instance.send_versions(relation)
        # Preserve behavior of raising version exceptions immediately.
        instance.get_data()
        return instance
    else:
        return None
