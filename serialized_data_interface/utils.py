import hashlib
import os
import time
from pathlib import Path
from zipfile import ZipFile, ZipInfo

import requests
import yaml


# Custom ZipFile class due to extractall not keeping file permissions
# Official Python bug: https://bugs.python.org/issue15795
class ZipFileWithPermissions(ZipFile):
    def extract(self, member, path=None, pwd=None):
        if not isinstance(member, ZipInfo):
            member = self.getinfo(member)

        if path is None:
            path = os.getcwd()

        ret_val = self._extract_member(member, path, pwd)
        attr = member.external_attr >> 16
        if attr != 0:
            os.chmod(ret_val, attr)
        return ret_val

    def extractall(self, path=None, members=None, pwd=None):
        if members is None:
            members = self.namelist()

        if path is None:
            path = os.getcwd()
        else:
            path = os.fspath(path)

        for zipinfo in members:
            self.extract(zipinfo, path, pwd)


def get_schema(schema):
    """Ensures schema is retrieved if necessary, then loads it."""

    if isinstance(schema, str):
        h = hashlib.md5()
        h.update(schema.encode("utf-8"))
        p = Path("/tmp") / h.hexdigest()
        if p.exists():
            return yaml.safe_load(p.read_text())
        else:
            for _ in range(30):
                try:
                    response = _get_schema_response_from_remote(schema)
                    break
                except requests.RequestException:
                    time.sleep(5)
            else:
                response = _get_schema_response_from_remote(schema)

            p.write_text(response.text)
            return yaml.safe_load(response.text)

    return schema


def _get_schema_response_from_remote(url: str) -> requests.Response:
    """
    Returns a schema response object from a remote location, observing proxy settings if available

    Raises for status if unsuccessful.

    proxy settings for each of http, https, and no_proxy are inferred from environment variables
    in the order:
        JUJU_HTTP(S)_PROXY/JUJU_NO_PROXY
        HTTP(S)_PROXY/NO_PROXY

    Args:
        url (str): String url to access the schema

    Returns:
        requests.Response: Schema as a Response object
    """
    proxies = _get_proxy_settings_from_env()
    response = requests.get(url=url, proxies=proxies)
    response.raise_for_status()
    return response


def _get_proxy_settings_from_env() -> dict:
    """Returns proxy settings dict inferred from environment"""
    proxies = {}
    proxies["http"] = (
        os.environ.get("JUJU_CHARM_HTTP_PROXY") or os.environ.get("HTTP_PROXY") or None
    )

    proxies["https"] = (
        os.environ.get("JUJU_CHARM_HTTPS_PROXY")
        or os.environ.get("HTTPS_PROXY")
        or None
    )

    proxies["no-proxy"] = (
        os.environ.get("JUJU_CHARM_NO_PROXY") or os.environ.get("NO_PROXY") or None
    )

    return proxies
