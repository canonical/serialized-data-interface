import yaml
from ops.testing import Harness
from ops.charm import CharmBase

from provide_interface import ProvideAppInterface


def test_app_provide():
    class ProvideCharm(CharmBase):
        def __init__(self, *args):
            super().__init__(*args)
            self.interface = ProvideAppInterface(
                self,
                "app-provides",
                "test/unit/test_schema.yaml",
            )

    harness = Harness(
        ProvideCharm,
        meta="""
        name: test-app
        provides:
            app-provides:
                interface: serialized-data
        """,
    )
    harness.set_leader(True)
    rel_id = harness.add_relation("app-provides", "test-app")
    data = {
        "service": "my-service",
        "port": 4242,
        "access-key": "my-access-key",
        "secret-key": "my-secret-key",
    }
    harness.begin()
    harness.charm.interface.update_relation_data(data)
    rel_data = harness.get_relation_data(rel_id, "test-app")
    assert rel_data["data"] == yaml.dump(data)
