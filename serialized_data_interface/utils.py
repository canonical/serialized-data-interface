from pathlib import Path
import hashlib
import time
import os
import yaml
from zipfile import ZipFile, ZipInfo

import requests


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
                    response = requests.get(schema)
                    response.raise_for_status()
                    break
                except requests.RequestException:
                    time.sleep(5)
            else:
                response = requests.get(schema)
                response.raise_for_status()

            p.write_text(response.text)
            return yaml.safe_load(response.text)

    return schema
