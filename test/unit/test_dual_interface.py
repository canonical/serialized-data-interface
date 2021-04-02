import yaml
from ops.charm import CharmBase
from ops.model import Application
from ops.testing import Harness

import serialized_data_interface as sdi


class RequiresCharm(CharmBase):
    def __init__(self, *args):
        super().__init__(*args)
        with open("test/unit/test_schema.yaml", "r") as schema:
            self.interface = sdi.SerializedDataInterface(
                self,
                "app-requires",
                yaml.safe_load(schema),
                {"v2"},
                "requires",
            )


def test_dual_interface_charm():
    harness = Harness(
        RequiresCharm,
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
    harness.update_relation_data(
        rel_id,
        "foo",
        {"data": "foo: bar"},
    )
    harness.begin()
    harness.charm.interface.send_data({"bar": None})

    rel_data = harness.charm.interface.get_data()
    assert rel_data == {
        (rel, app): {"bar": None} if app._is_our_app else {"foo": "bar"}
        for rel in harness.model.relations["app-requires"]
        for app, bag in rel.data.items()
        if isinstance(app, Application) and "data" in bag
    }
