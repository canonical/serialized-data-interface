# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

from unittest.mock import MagicMock, mock_open

import pytest

import serialized_data_interface as sdi


def test_working(mocker):
    metadata = """
requires:
  xyzzy:
    interface: foo
    schema: {}
    versions: [v1]
"""

    mocker.patch("builtins.open", mock_open(read_data=metadata))
    mocker.patch.object(sdi, "SerializedDataInterface")
    mocker.patch.object(
        sdi.utils, "get_schema", MagicMock(return_value={"v1": {"requires": {}}})
    )

    relation = MagicMock()
    relation.name = "rel"
    relation.id = 1
    relation.app.name = "charm"
    charm = MagicMock(
        name="charm",
        **{
            "meta.relations": {"xyzzy": MagicMock(**{"role.name": "requires"})},
            "model.relations": {"xyzzy": [relation]},
        }
    )
    relation.data = {
        charm.app: {"_supported_versions": "- v1\n"},
        relation.app: {"_supported_versions": "- v1\n"},
    }
    interface = sdi.get_interface(charm, "xyzzy")

    assert interface is not None


def test_no_existing_relation(mocker):
    metadata = """
requires:
  thud:
    interface: thud
    schema: {}
    versions: []
"""

    mocker.patch("builtins.open", mock_open(read_data=metadata))

    charm = MagicMock(
        name="charm",
        **{"meta.relations": {"thud": MagicMock(**{"role.name": "requires"})}}
    )
    interface = sdi.get_interface(charm, "thud")

    assert interface is None


def test_invalid_name(mocker):
    metadata = """
requires:
  👨‍👩‍👦:
"""

    mocker.patch("builtins.open", mock_open(read_data=metadata))

    with pytest.raises(sdi.InvalidRelationName):
        sdi.get_interface(MagicMock(name="charm"), "🐈‍⬛")
