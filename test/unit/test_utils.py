# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import os
from unittest import mock

import pytest
import requests
import yaml

from serialized_data_interface.utils import (
    _get_proxy_settings_from_env,
    _get_schema_response_from_remote,
    get_schema,
)


def test_get_schema():
    with open("test/unit/metadata_in.yaml") as metadata_in_file:
        metadata_in = yaml.safe_load(metadata_in_file)

    with open("test/unit/metadata_out.yaml") as metadata_out_file:
        metadata_out = yaml.safe_load(metadata_out_file)

    test_schema_filename = "test/unit/test_schema.yaml"
    with open(test_schema_filename) as test_schema_file:
        test_schema = yaml.safe_load(test_schema_file)

    schema_url = metadata_in["provides"]["oidc-client"]["schema"]

    # With URL
    schema = get_schema(schema_url)

    assert schema == metadata_out["provides"]["oidc-client"]["schema"]

    # With Dict
    schema = get_schema(metadata_out["provides"]["oidc-client"]["schema"])

    assert schema == metadata_out["provides"]["oidc-client"]["schema"]


PROXY_URLS = {i: f"http://a:800{str(i)}" for i in range(6)}


def mocked_requests_get(*args, **kwargs):
    """Mocked response so the code doesn't raise an exception"""
    response = requests.Response()
    response.status_code = 200
    response._content = str.encode("{'some': 'yaml'}")
    return response


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
            },
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
            },
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
            },
        ),
    ],
)
def test_get_proxy_settings_from_env(env_dict, expected_proxies):
    # Patch the environment with our proxy settings
    with mock.patch.dict(os.environ, env_dict, clear=True):
        proxies = _get_proxy_settings_from_env()
        assert proxies == expected_proxies

        with mock.patch(
            "serialized_data_interface.utils.requests.get",
            side_effect=mocked_requests_get,
        ):
            url = ""
            _get_schema_response_from_remote(url)
            requests.get.assert_called_with(url=url, proxies=expected_proxies)
