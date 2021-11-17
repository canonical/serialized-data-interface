from unittest.mock import MagicMock, mock_open

import pytest

import serialized_data_interface as sdi


def test_working(mocker):
    metadata = """
requires:
  xyzzy:
    interface: foo
    schema: ~
    versions: []
"""

    mocker.patch("builtins.open", mock_open(read_data=metadata))
    mocker.patch.object(sdi, "SerializedDataInterface")
    mocker.patch.object(sdi, "get_schema", MagicMock())

    charm = MagicMock()
    charm.model.relations = {"xyzzy"}
    interface = sdi.get_interface(charm, "xyzzy")

    assert interface is not None


def test_no_existing_relation(mocker):
    metadata = """
requires:
  thud:
"""

    mocker.patch("builtins.open", mock_open(read_data=metadata))

    interface = sdi.get_interface(MagicMock(), "thud")

    assert interface is None


def test_invalid_name(mocker):
    metadata = """
requires:
  👨‍👩‍👦:
"""

    mocker.patch("builtins.open", mock_open(read_data=metadata))

    with pytest.raises(sdi.InvalidRelationName):
        sdi.get_interface(None, "🐈‍⬛")


def test_dupes(mocker):
    metadata = """
requires:
  ほげ:
  bar:
provides:
  ほげ:
  bar:
"""

    mocker.patch("builtins.open", mock_open(read_data=metadata))

    expected = "Relations defined in both requires and provides: bar, ほげ"
    with pytest.raises(sdi.DuplicateRelation, match=expected):
        sdi.get_interface(None, "foo")
