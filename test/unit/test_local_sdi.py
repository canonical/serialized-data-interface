# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import os
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile

import yaml

import serialized_data_interface.local_sdi as local_sdi


METADATA_IN = "test/unit/metadata_in.yaml"
METADATA_OUT = "test/unit/metadata_out.yaml"


def test_localize_metadata_schema():
    with open(METADATA_IN) as metadata_in_file:
        metadata_in = yaml.safe_load(metadata_in_file)
    new_metadata = local_sdi.localize_metadata_schema(metadata_in)

    with open(METADATA_OUT) as metadata_out_file:
        metadata_out = yaml.safe_load(metadata_out_file)
    assert metadata_out == new_metadata


def test_change_zip_file():
    with ZipFile("test.charm", "w", ZIP_DEFLATED) as test_zip:
        test_zip.write(METADATA_IN, "metadata.yaml")

    with open(METADATA_OUT) as metadata_out_file:
        metadata_out = yaml.safe_load(metadata_out_file)

    local_sdi.change_zip_file("test", metadata_out)

    with ZipFile("test.charm", "r") as test_zip:
        zip_metadata = yaml.safe_load(test_zip.open("metadata.yaml"))

    assert metadata_out == zip_metadata

    os.remove("test.charm")


def test_localize_metadata_file():

    with TemporaryDirectory() as temp_dir:
        metadata_in_file = os.path.join(temp_dir, "metadata_in.yaml")
        shutil.copy(METADATA_IN, metadata_in_file)

        local_sdi.localize_metadata_file(metadata_in_file)

        # Don't load this as a yaml, just as string, so that we don't ignore any changes to
        # key order or comments
        metadata_localized_as_str = Path(metadata_in_file).read_text()
        metadata_out_as_str = Path(METADATA_OUT).read_text()

        assert metadata_localized_as_str == metadata_out_as_str
