# Copyright 2023 Canonical Ltd.
import yaml
from ops.charm import CharmBase
from ops.model import Application
from ops.testing import Harness

from serialized_data_interface.sdi import SerializedDataInterface


class ProvideCharm(CharmBase):
    def __init__(self, *args):
        super().__init__(*args)
        with open("test/unit/test_schema.yaml", "r") as schema:
            self.interface = SerializedDataInterface(
                self,
                "app-provides",
                yaml.safe_load(schema),
                {"v1"},
                "provides",
            )


def test_provide_no_relation():
    harness = Harness(
        ProvideCharm,
        meta="""
        name: test-app
        requires:
            app-provides:
                interface: serialized-data
        """,
    )
    harness.set_leader(True)
    harness.begin()


def test_provide_one_relation():
    harness = Harness(
        ProvideCharm,
        meta="""
        name: test-app
        requires:
            app-provides:
                interface: serialized-data
        """,
    )
    harness.set_leader(True)
    rel_id = harness.add_relation("app-provides", "foo")
    harness.add_relation_unit(rel_id, "foo/0")
    harness.update_relation_data(
        rel_id,
        "foo",
        {"_supported_versions": yaml.dump(["v1"])},
    )
    harness.begin()
    assert harness.charm.interface.get_data() == {}

    data = {
        "service": "my-service",
        "port": 4242,
        "access-key": "my-access-key",
        "secret-key": "my-secret-key",
    }
    harness.charm.interface.send_data(data)
    rel_data = harness.charm.interface.get_data()
    assert rel_data == {
        (rel, app): data
        for rel in harness.model.relations["app-provides"]
        for app, bag in rel.data.items()
        if isinstance(app, Application) and "data" in bag
    }


def test_provide_many_relations():
    harness = Harness(
        ProvideCharm,
        meta="""
        name: test-app
        requires:
            app-provides:
                interface: serialized-data
        """,
    )
    harness.set_leader(True)
    rel_id1 = harness.add_relation("app-provides", "foo")
    harness.add_relation_unit(rel_id1, "foo/0")
    harness.update_relation_data(
        rel_id1,
        "foo",
        {"_supported_versions": yaml.dump(["v1"])},
    )
    rel_id2 = harness.add_relation("app-provides", "bar")
    harness.add_relation_unit(rel_id2, "bar/0")
    harness.update_relation_data(
        rel_id2,
        "bar",
        {"_supported_versions": yaml.dump(["v1"])},
    )
    harness.begin()

    data = {
        "service": "my-service",
        "port": 4242,
        "access-key": "my-access-key",
        "secret-key": "my-secret-key",
    }
    harness.charm.interface.send_data(data)
    rel_data = harness.charm.interface.get_data()
    assert rel_data == {
        (rel, app): data
        for rel in harness.model.relations["app-provides"]
        for app, bag in rel.data.items()
        if isinstance(app, Application) and "data" in bag
    }
