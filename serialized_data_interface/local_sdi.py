import os
from zipfile import ZipFile, ZIP_DEFLATED
from pathlib import Path
from shutil import rmtree

import yaml
from .utils import get_schema, ZipFileWithPermissions


def create_new_metadata(metadata):
    for name, interface in metadata.get("provides", {}).items():
        if "schema" in metadata["provides"][name]:
            metadata["provides"][name]["schema"] = get_schema(interface["schema"])

    for name, interface in metadata.get("requires", {}).items():
        if "schema" in metadata["requires"][name]:
            metadata["requires"][name]["schema"] = get_schema(interface["schema"])

    return metadata


def change_zip_file(charm_name, metadata):
    temp_dir = f"{charm_name}.tmp"
    charm_zip = f"{charm_name}.charm"

    os.mkdir(temp_dir)

    with ZipFileWithPermissions(f"{charm_name}.charm") as old_zip:
        old_zip.extractall(path=temp_dir)

    os.remove(charm_zip)

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
                    new_zip.write(str(filepath), str(filepath.relative_to(temp_dir)))

    rmtree(temp_dir)


def main():
    with open("metadata.yaml", "r") as metadata_file:
        metadata = yaml.safe_load(metadata_file)

    metadata = create_new_metadata(metadata)

    charm_name = metadata["name"]

    change_zip_file(charm_name, metadata)


if __name__ == "__main__":
    main()
