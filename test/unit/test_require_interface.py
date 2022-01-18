import pytest
import yaml
from unittest.mock import MagicMock

from ops.charm import CharmBase
from ops.model import Application, RelationDataError, ModelError
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


def test_not_leader():
    received_data = {
        "service": "my-service",
        "port": 4242,
        "access-key": "my-access-key",
        "secret-key": "my-secret-key",
    }
    sent_data = {"response": "ok"}

    harness = Harness(
        RequireCharm,
        meta="""
        name: test-app
        requires:
            app-requires:
                interface: serialized-data
        """,
    )
    harness.set_leader(False)
    rel_id = harness.add_relation("app-requires", "foo")
    harness.add_relation_unit(rel_id, "foo/0")
    harness.update_relation_data(
        rel_id,
        "foo",
        {
            "_supported_versions": yaml.dump(["v1"]),
            "data": yaml.dump(received_data),
        },
    )
    harness.begin()

    # confirm that reading remote data doesn't require leadership
    rel = harness.charm.model.get_relation("app-requires", rel_id)
    assert harness.charm.interface.get_data() == {
        (rel, rel.app): received_data,
    }

    # confirm that sending data still requires leadership
    with pytest.raises(RelationDataError):
        harness.charm.interface.send_data(sent_data)
    harness.set_leader(True)
    harness.charm.interface.send_data(sent_data)

    # confirm that leader can see sent data
    assert harness.charm.interface.get_data() == {
        (rel, rel.app): received_data,
        (rel, harness.charm.app): sent_data,
    }

    # confirm that non-leader cannot see sent data
    harness.set_leader(False)
    assert harness.charm.interface.get_data() == {
        (rel, rel.app): received_data,
    }


def test_missing_remote_app_name():
    exploding_bag = MagicMock()
    exploding_bag.__getitem__.side_effect = ModelError(
        b'ERROR "" is not a valid unit or application\n'
    )
    exploding_bag.copy.return_value = exploding_bag

    harness = Harness(
        RequireCharm,
        meta="""
        name: test-app
        requires:
            app-requires:
                interface: serialized-data
        """,
    )
    harness.set_leader(False)
    rel_id = harness.add_relation("app-requires", "")
    # not ideal, but I couldn't get it to work w/ harness.update_relation_data()
    # due to it doing several copy operations internally
    harness._backend._relation_data[rel_id][""] = exploding_bag

    # confirm that setting up the charm does not explode
    harness.begin()
