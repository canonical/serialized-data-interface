# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.
from typing import Set, Union

from ops.model import Application, Relation, Unit


class SDIException(Exception):
    """Base exception for exceptions from this library."""


class InvalidRoleError(SDIException):
    """The specified role is not one of "provides", "requires", or "peer".

    The following property is available:

        * role: The role which was invalid.
    """

    def __init__(self, role):
        """Initialize the exception.

        Args:
            role: The given role which was invalid.
        """
        super().__init__(role)
        self.role = role


class InvalidAppNameError(SDIException):
    """The send_data method was called with an invalid app name.

    Attributes:
        app_name: Name of the app which is invalid.
    """

    def __init__(self, app_name: str):
        super().__init__(app_name)
        self.app_name = app_name


class UnknownEndpointError(SDIException):
    """The given relation endpoint name is was not found in metadata.yaml."""


# Deprecated alias.
InvalidRelationName = UnknownEndpointError


class SchemaError(SDIException):
    """Base class for errors with the schema."""


class SchemaParseError(SchemaError):
    """There was an error parsing the schemas YAML."""


class InvalidSchemaError(SchemaError):
    """An invalid schema (not a valid JSONSchema) was found in the schema doc.

    Attributes:
        version: The version of the schema which was invalid.
    """

    def __init__(self, version: Union[int, str]):
        super().__init__(version)
        self.version = version


class InvalidSchemaVersionError(InvalidSchemaError):
    """An invalid version (not an int nor "vX" string) was found in the schema doc.

    Attributes:
        version: The schema version which was invalid.
    """


class RelationException(SDIException):
    """Base exception for relation exceptions from this library."""

    def __init__(self, relation: Relation):
        super().__init__(f"{relation.name}:{relation.id}")
        self.relation = relation


class UnversionedRelation(RelationException):
    """The relation is not yet complete due to missing remote version info."""


# Deprecated alias.
NoVersionsListed = UnversionedRelation


class IncompleteRelation(RelationException):
    """The relation is not yet complete due to missing remote data."""


class RelationError(RelationException):
    """Base class for actual errors from this library."""


class IncompatibleVersionsError(RelationError):
    """The remote application does not support any common schema versions.

    Attributes:
        relation: The relation which failed.
        local_versions: The set of versions supported by the local side.
        remote_versions: The set of versions supported by the remote side.
    """

    def __init__(
        self,
        relation: Relation,
        local_versions: Set[Union[int, str]],
        remote_versions: Set[Union[int, str]],
    ):
        self.args = (
            f"{relation.name}:{relation.id} {list(local_versions)} {list(remote_versions)}",
        )
        self.relation = relation
        self.local_versions = local_versions
        self.remote_versions = remote_versions


# Deprecated alias.
NoCompatibleVersions = IncompatibleVersionsError


class RelationParseError(RelationError):
    """An error was encountered parsing data from the relation.

    Attributes:
        relation: The Relation which caused the exception.
        entity: The Application or Unit which caused the exception.
        key: The data key which caused the exception.
    """

    def __init__(self, relation: Relation, entity: Union[Application, Unit], key: str):
        super().__init__(relation)
        self.args = (f"{relation.name}:{relation.id} {entity.name} '{key}'",)
        self.relation = relation
        self.entity = entity
        self.key = key


class RelationDataError(RelationError):
    """An error was encountered validating data against the schema.

    Attributes:
        relation: The Relation which caused the exception.
        entity: The Application or Unit which caused the exception.
    """

    def __init__(self, relation: Relation, entity: Union[Application, Unit]):
        super().__init__(relation)
        self.args = (f"{relation.name}:{relation.id} {entity.name}",)
        self.relation = relation
        self.entity = entity


class MissingSchemaError(SchemaError, RelationDataError):
    """Data was found in a relation which didn't have a matching schema.

    Attributes:
        relation: The Relation which caused the exception.
        role: The role of the schema which couldn't be found.
        entity: The Application or Unit which caused the exception.
    """

    def __init__(self, relation: Relation, role: str, entity: Union[Application, Unit]):
        self.args = (f"{relation.name}:{relation.id} {role} {entity.name}",)
        self.relation = relation
        self.role = role
        self.entity = entity


class RelationPermissionError(RelationDataError):
    """An attempt to write data to a disallowed bucket."""


class NoSchemaDefined(SDIException):
    """A schema was referenced but could not be found.

    Attributes:
        version: The version which is missing a schema.
        role: The role which is missing a schema.
    """

    def __init__(self, version: Union[int, str], role: str):
        super().__init__(f"{version} {role}")
        self.version = version
        self.role = role
