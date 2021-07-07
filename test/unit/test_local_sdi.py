import yaml
import os
from zipfile import ZipFile, ZIP_DEFLATED

import serialized_data_interface.local_sdi as local_sdi


def test_create_new_metadata():
    with open("test/unit/metadata_in.yaml") as metadata_in_file:
        metadata_in = yaml.safe_load(metadata_in_file)
    new_metadata = local_sdi.create_new_metadata(metadata_in)

    with open("test/unit/metadata_out.yaml") as metadata_out_file:
        metadata_out = yaml.safe_load(metadata_out_file)
    assert metadata_out == new_metadata


def test_change_zip_file():
    with ZipFile("test.charm", "w", ZIP_DEFLATED) as test_zip:
        test_zip.write("test/unit/metadata_in.yaml", "metadata.yaml")

    with open("test/unit/metadata_out.yaml") as metadata_out_file:
        metadata_out = yaml.safe_load(metadata_out_file)

    local_sdi.change_zip_file("test", metadata_out)

    with ZipFile("test.charm", "r") as test_zip:
        zip_metadata = yaml.safe_load(test_zip.open("metadata.yaml"))

    assert metadata_out == zip_metadata

    os.remove("test.charm")
