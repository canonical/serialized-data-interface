import pytest
import yaml
from ops.charm import CharmBase
from ops.model import Application
from ops.testing import Harness

import serialized_data_interface as sdi


class RequireCharm(CharmBase):
    def __init__(self, *args):
        super().__init__(*args)
        with open("test/unit/test_schema.yaml", "r") as schema:
            self.interface = sdi.SerializedDataInterface(
                self,
                "app-requires",
                yaml.safe_load(schema),
                {"v1"},
                "requires",
            )


def test_require_no_relation():
    harness = Harness(
        RequireCharm,
        meta="""
        name: test-app
        requires:
            app-requires:
                interface: serialized-data
        """,
    )
    harness.set_leader(True)
    harness.begin()


def test_require_one_relation():
    harness = Harness(
        RequireCharm,
        meta="""
        name: test-app
        requires:
            app-requires:
                interface: serialized-data
        """,
    )
    harness.set_leader(True)
    rel_id = harness.add_relation("app-requires", "foo")
    harness.add_relation_unit(rel_id, "foo/0")
    harness.update_relation_data(
        rel_id,
        "foo",
        {"_supported_versions": yaml.dump(["v1"])},
    )
    harness.begin()
    data = {
        "service": "my-service",
        "port": 4242,
        "access-key": "my-access-key",
        "secret-key": "my-secret-key",
    }
    harness.update_relation_data(rel_id, "foo", {"data": yaml.dump(data)})

    rel_data = harness.charm.interface.get_data()
    assert rel_data == {
        (rel, app): data
        for rel in harness.model.relations["app-requires"]
        for app, bag in rel.data.items()
        if isinstance(app, Application) and "data" in bag
    }


def test_version_mismatch():
    harness = Harness(
        RequireCharm,
        meta="""
        name: test-app
        requires:
            app-requires:
                interface: serialized-data
        """,
    )
    harness.set_leader(True)
    rel_id = harness.add_relation("app-requires", "foo")
    harness.add_relation_unit(rel_id, "foo/0")
    harness.update_relation_data(
        rel_id,
        "foo",
        {"_supported_versions": yaml.dump(["v2"])},
    )
    with pytest.raises(sdi.NoCompatibleVersions):
        harness.begin()
