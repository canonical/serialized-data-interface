import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile

import yaml

from .utils import ZipFileWithPermissions, get_schema


def create_new_metadata(metadata):
    for name, interface in metadata.get("provides", {}).items():
        if "schema" in metadata["provides"][name]:
            metadata["provides"][name]["schema"] = get_schema(interface["schema"])

    for name, interface in metadata.get("requires", {}).items():
        if "schema" in metadata["requires"][name]:
            metadata["requires"][name]["schema"] = get_schema(interface["schema"])

    return metadata


def change_zip_file(charm_name, metadata, charm_path="."):
    charm_zip = f"{charm_path}/{charm_name}.charm"

    with TemporaryDirectory() as temp_dir:
        with ZipFileWithPermissions(charm_zip) as old_zip:
            old_zip.extractall(path=temp_dir)

        with ZipFile(charm_zip, "w", ZIP_DEFLATED) as new_zip:
            for dirpath, dirnames, filenames in os.walk(temp_dir, followlinks=True):
                dirpath = Path(dirpath)
                for filename in filenames:
                    filepath = dirpath / filename
                    if "metadata.yaml" in filename:
                        new_zip.writestr(
                            str(filepath.relative_to(temp_dir)), yaml.dump(metadata)
                        )
                    else:
                        new_zip.write(filepath, filepath.relative_to(temp_dir))


def main(charm_path="."):
    with open(f"{charm_path}/metadata.yaml", "r") as metadata_file:
        metadata = yaml.safe_load(metadata_file)

    metadata = create_new_metadata(metadata)

    charm_name = metadata["name"]

    change_zip_file(charm_name, metadata, charm_path)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        main(".")
