import yaml

import serialized_data_interface.local_sdi as local_sdi


def test_get_schema():
    with open("test/unit/metadata_in.yaml") as metadata_in_file:
        metadata_in = yaml.safe_load(metadata_in_file)

    with open("test/unit/metadata_out.yaml") as metadata_out_file:
        metadata_out = yaml.safe_load(metadata_out_file)

    schema_url = metadata_in["provides"]["oidc-client"]["schema"]

    # With URL
    schema = local_sdi.get_schema(schema_url)

    assert schema == metadata_out["provides"]["oidc-client"]["schema"]

    # With Dict
    schema = local_sdi.get_schema(metadata_out["provides"]["oidc-client"]["schema"])

    assert schema == metadata_out["provides"]["oidc-client"]["schema"]
