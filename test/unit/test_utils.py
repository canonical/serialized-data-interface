import os
import pytest
from unittest import mock
import yaml

import serialized_data_interface.local_sdi as local_sdi
from serialized_data_interface.utils import _get_proxy_settings_from_env


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


PROXY_URLS = {i: f"http://a:800{str(i)}" for i in range(6)}


@pytest.mark.parametrize(
    "env_dict, expected_proxies",
    [
        # Null test
        ({}, {"http": None, "https": None, "no-proxy": None}),
        # Typical proxy args
        (
                {
                    "HTTP_PROXY": PROXY_URLS[0],
                    "HTTPS_PROXY": PROXY_URLS[1],
                    "NO_PROXY": PROXY_URLS[2],
                },
                {
                    "http": PROXY_URLS[0],
                    "https": PROXY_URLS[1],
                    "no-proxy": PROXY_URLS[2],
                }
        ),
        # Juju proxy args
        (
                {
                    "JUJU_CHARM_HTTP_PROXY": PROXY_URLS[0],
                    "JUJU_CHARM_HTTPS_PROXY": PROXY_URLS[1],
                    "JUJU_CHARM_NO_PROXY": PROXY_URLS[2],
                },
                {
                    "http": PROXY_URLS[0],
                    "https": PROXY_URLS[1],
                    "no-proxy": PROXY_URLS[2],
                }
        ),
        # Ensure Juju take priority over regular proxy
        (
                {
                    "JUJU_CHARM_HTTP_PROXY": PROXY_URLS[0],
                    "JUJU_CHARM_HTTPS_PROXY": PROXY_URLS[1],
                    "JUJU_CHARM_NO_PROXY": PROXY_URLS[2],
                    "HTTP_PROXY": PROXY_URLS[3],
                    "HTTPS_PROXY": PROXY_URLS[4],
                    "NO_PROXY": PROXY_URLS[5],
                },
                {
                    "http": PROXY_URLS[0],
                    "https": PROXY_URLS[1],
                    "no-proxy": PROXY_URLS[2],
                }
        ),
    ]
)
def test_get_proxy_settings_from_env(env_dict, expected_proxies):
    # Patch the environment with our proxy settings
    with mock.patch.dict(os.environ, env_dict, clear=True):
        proxies = _get_proxy_settings_from_env()
        assert proxies == expected_proxies


# TODO (ca-scribner): Need a test that simulates a proxy to ensure we can get
#  schema through a proxy.  Or, at least mock requests to make sure it gets
#  an expected call?
