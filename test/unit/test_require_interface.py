import yaml
from ops.testing import Harness
from ops.charm import CharmBase

from require_interface import RequireAppInterface


class RequireCharm(CharmBase):
    def __init__(self, *args):
        super().__init__(*args)
        self.interface = RequireAppInterface(
            self, "app-requires", "test/unit/test_schema.yaml"
        )


def test_require():
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
    rel_id = harness.add_relation("app-requires", "test-app2")
    harness.begin()
    assert harness.charm.interface.is_created
    assert not harness.charm.interface.is_available
    harness.add_relation_unit(rel_id, "test-app2/0")
    data = {
        "service": "my-service",
        "port": 4242,
        "access-key": "my-access-key",
        "secret-key": "my-secret-key",
    }
    harness.update_relation_data(rel_id, "test-app2", {"data": yaml.dump(data)})
    assert harness.charm.interface.is_available

    rel_data = harness.charm.interface.data[0]
    assert rel_data == data


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
    assert not harness.charm.interface.is_created
    assert not harness.charm.interface.is_available
