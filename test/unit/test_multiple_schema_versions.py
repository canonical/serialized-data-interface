import pytest
import serialized_data_interface as sdi
import yaml
from ops.charm import CharmBase
from ops.testing import Harness
from jsonschema.exceptions import ValidationError


class ProvideCharm(CharmBase):
    def __init__(self, *args):
        super().__init__(*args)
        with open("test/unit/test_schema.yaml", "r") as schema:
            self.interface = sdi.SerializedDataInterface(
                self,
                "app-provides",
                yaml.safe_load(schema),
                {"v1", "v2"},
                "provides",
            )


def test_send_data_multiple_versions():
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

    rel_id1 = harness.add_relation("app-provides", "appv1")
    harness.add_relation_unit(rel_id1, "appv1/0")
    harness.update_relation_data(
        rel_id1,
        "appv1",
        {"_supported_versions": "- v1"},
    )

    rel_id2 = harness.add_relation("app-provides", "appv2")
    harness.add_relation_unit(rel_id2, "appv2/0")
    harness.update_relation_data(
        rel_id2,
        "appv2",
        {"_supported_versions": "- v2"},
    )

    harness.begin()
    data = {
        "service": "my-service",
        "port": 4242,
        "access-key": "my-access-key",
        "secret-key": "my-secret-key",
    }
    harness.update_relation_data(rel_id1, "appv1", {"data": yaml.dump(data)})
    harness.update_relation_data(rel_id2, "appv2", {"data": yaml.dump(data)})

    harness.charm.interface.send_data(data, "appv1")
    harness.charm.interface.send_data(
        {"foo": "sillema sillema nika su"},
        app_name="appv2",
    )

    # Can't send for an invalid app
    with pytest.raises(sdi.InvalidAppName):
        harness.charm.interface.send_data({}, "invalid-app")

    # Can't send across all apps if there's multiple versions
    with pytest.raises(sdi.AppNameOmitted):
        harness.charm.interface.send_data(data)

    # Can't send invalid data
    with pytest.raises(ValidationError):
        harness.charm.interface.send_data({}, "appv2")
