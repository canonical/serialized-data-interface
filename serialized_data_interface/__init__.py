from typing import Dict, Optional, Set, Tuple

import yaml
from jsonschema import validate
from ops.charm import CharmBase
from ops.model import Application, Relation

from .utils import get_schema

__all__ = [
    "AppNameOmitted",
    "InvalidAppName",
    "NoCompatibleVersions",
    "NoSchemaDefined",
    "NoVersionsListed",
    "get_interfaces",
]


class NoCompatibleVersions(Exception):
    def __init__(self, relation, apps):
        self.relation = relation
        self.apps = ", ".join(apps)

    def __str__(self):
        return f"No compatible {self.relation} versions found for apps: {self.apps}"


class NoSchemaDefined(Exception):
    def __init__(self, end):
        self.end = end

    def __str__(self):
        return (
            f"Calling send_data from the {self.end} end of a relation "
            f"requires defining a {self.end} section in the schema."
        )


class NoVersionsListed(Exception):
    def __init__(self, relation, apps):
        self.relation = relation
        self.apps = ", ".join(apps)

    def __str__(self):
        return f"List of {self.relation} versions not found for apps: {self.apps}"


class AppNameOmitted(Exception):
    def __init__(self, relation, versions):
        self.relation = relation
        self.versions = versions

    def __str__(self):
        versions = list(self.versions.values())
        return (
            "Sending data across multiple relations with different "
            "schema versions requires `app_name` to be passed in. "
            f"Found versions {versions} for relation {self.relation}"
        )


class InvalidAppName(Exception):
    def __init__(self, relation, app_name):
        self.relation = relation
        self.app_name = app_name

    def __str__(self):
        return f"Application {self.app_name} not found for relation {self.relation}"


class InvalidRelationName(Exception):
    def __init__(self, relation):
        self.relation = relation

    def __str__(self):
        return f"Relation {self.relation} not found in metadata.yaml"


class DuplicateRelation(Exception):
    def __init__(self, relations):
        self.relations = relations

    def __str__(self):
        rels = ", ".join(self.relations)
        return f"Relations defined in both requires and provides: {rels}"


class SerializedDataInterface:
    """Represents a schema-defined interface between two charms.

    The schema should match the JSON Schema specification, though
    should be written in YAML.
    """

    def __init__(
        self,
        charm: CharmBase,
        relation_name: str,
        schema: dict,
        versions: Set[str],
        end: str,
    ):
        for relation in charm.model.relations[relation_name]:
            relation.data[charm.app]["_supported_versions"] = yaml.dump(list(versions))

        others = {
            app.name: bag.get("_supported_versions")
            for relation in charm.model.relations[relation_name]
            for app, bag in relation.data.items()
            if isinstance(app, Application) and not app._is_our_app
        }

        unversioned = [name for name, versions in others.items() if versions is None]
        if unversioned:
            raise NoVersionsListed(relation_name, unversioned)

        compatibility = {
            name: set.intersection(versions, set(yaml.safe_load(other_versions)))
            for name, other_versions in others.items()
        }
        incompatible = [
            name for name, versions in compatibility.items() if not versions
        ]
        if incompatible:
            raise NoCompatibleVersions(relation_name, incompatible)

        self.charm = charm
        self.relation_name = relation_name
        # Grab the latest compatible API version(s). Assume all version names are in the form of
        # `vX`, where `X` is a potentially multi-digit integer. For example, v1, v2, v12.
        self.versions = {
            name: sorted(vs, key=lambda x: -int(x[1:]))[0]
            for name, vs in compatibility.items()
        }
        self.schema = schema
        self.end = end

    def __repr__(self):
        return (
            f"SerializedDataInterface(charm={self.charm}, relation_name={self.relation_name}, "
            f"schema={self.schema}, versions={self.versions}, end={self.end})"
        )

    @property
    def _relations(self):
        return [
            rel for rel in self.charm.model.relations[self.relation_name] if rel.app
        ]

    def get_data(self) -> Dict[Tuple[Relation, Application], Dict]:
        other = {
            "provides": "requires",
            "requires": "provides",
        }[self.end]

        data = {
            (relation, app): yaml.safe_load(bag["data"])
            for relation in self._relations
            for app, bag in relation.data.items()
            if isinstance(app, Application) and "data" in bag
        }

        for (rel, app), datum in data.items():
            if datum:
                schema = self.schema[self.versions[rel.app.name]]
                if app._is_our_app:
                    schema = schema[self.end]
                else:
                    schema = schema[other]

                validate(instance=datum, schema=schema)

        return data

    def send_data(self, data: dict, app_name: str = None):
        """Send data to related app(s).

        `app_name` may be omitted if all related apps are on the same version of the schema.
        Otherwise, it must be specified. Data is validated by the relation schema before being
        sent.
        """

        # self.versions looks like this example:
        #
        #     {'foo': 'v1', 'bar': 'v2', 'baz': 'v3'}
        #
        # Where `foo`, `bar`, and `baz` are related application names, and `v1`, `v2`, `v3`
        # are the agreed-upon schema versions. First, we check to make sure that either:
        #
        #  - `app_name` is defined, or
        #  - all related apps are using the same schema version
        if len(set(self.versions.values())) != 1 and app_name is None:
            raise AppNameOmitted(self.relation_name, self.versions)

        # Then, we ensure that `app_name` is actually a valid related application
        # by filtering out any related apps that don't match the name, and raising an error
        # if the resulting list is empty.
        relations = self._relations

        if app_name is not None:
            relations = [r for r in relations if r.app.name == app_name]

        if not relations:
            raise InvalidAppName(self.relation_name, app_name)

        serialized = yaml.dump(data)
        for rel in relations:
            try:
                schema = self.schema[self.versions[rel.app.name]][self.end]
            except KeyError:
                raise NoSchemaDefined(self.end)

            validate(instance=data, schema=schema)
            rel.data[self.charm.app]["data"] = serialized


def get_interfaces(charm) -> Dict[str, Optional[SerializedDataInterface]]:
    """Reads metadata.yaml to retrieve schema-checked interface objects.

    The returned dictionary will always contain keys for each interface that
    defines a schema, but the associated values may be None, if no relations
    have been made yet on that interface. This is because instantiating the
    SerializedDataInterface class requires agreeing on a schema version by
    both sides of the relation.
    """

    with open("metadata.yaml") as f:
        metadata = yaml.safe_load(f)

    # Ensure we don't have any duplicate keys across both provides and requires
    dupes = set.intersection(
        set(metadata.get("provides", {}).keys()),
        set(metadata.get("requires", {}).keys()),
    )
    assert not dupes, f"Found duplicate keys in provides/requires: {dupes}"

    provides = {
        name: SerializedDataInterface(
            charm,
            name,
            get_schema(interface["schema"]),
            set(interface["versions"]),
            "provides",
        )
        if charm.model.relations[name]
        else None
        for name, interface in metadata.get("provides", {}).items()
        if "schema" in interface
    }

    requires = {
        name: SerializedDataInterface(
            charm,
            name,
            get_schema(interface["schema"]),
            set(interface["versions"]),
            "requires",
        )
        if charm.model.relations[name]
        else None
        for name, interface in metadata.get("requires", {}).items()
        if "schema" in interface
    }

    return {**provides, **requires}


def get_interface(charm, interface_name: str) -> Optional[SerializedDataInterface]:
    """Reads metadata.yaml to retrieve schema-checked interface object.

    The returned value may be None, if no relations have been made yet on that interface. This is
    because instantiating the SerializedDataInterface class requires agreeing on a schema version by
    both sides of the relation.
    """

    with open("metadata.yaml") as f:
        metadata = yaml.safe_load(f)

    # Ensure we don't have any duplicate keys across both provides and requires
    dupes = set.intersection(
        set(metadata.get("provides", {}).keys()),
        set(metadata.get("requires", {}).keys()),
    )

    if dupes:
        raise DuplicateRelation(sorted(dupes))

    relations = {**metadata.get("provides", {}), **metadata.get("requires", {})}

    try:
        interface = relations[interface_name]
    except KeyError:
        raise InvalidRelationName(interface_name)

    if interface_name not in charm.model.relations:
        return None

    return SerializedDataInterface(
        charm,
        interface_name,
        get_schema(interface["schema"]),
        set(interface["versions"]),
        "provides" if interface_name in metadata.get("provides", {}) else "requires",
    )
