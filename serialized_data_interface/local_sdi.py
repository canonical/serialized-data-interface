# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import os
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile

from ruamel.yaml import YAML
import typer
import yaml

from .utils import ZipFileWithPermissions, get_schema


def localize_metadata_schema(metadata):
    """Modifies metadata in place to in-line remote schema references."""
    for relation_type in ["requires", "provides"]:
        for name, interface in metadata.get(relation_type, {}).items():
            if "schema" in metadata[relation_type][name]:
                metadata[relation_type][name]["__schema_source"] = metadata[
                    relation_type
                ][name]["schema"]
                metadata[relation_type][name]["schema"] = get_schema(
                    interface["schema"]
                )

    return metadata


def localize_metadata_file(metadata_path):
    """Given a metadata file, localize any remote schema references in place."""
    metadata_file = Path(metadata_path)
    yaml_handler = YAML()
    yaml_handler.preserve_quotes = True
    metadata = yaml_handler.load(metadata_file.read_text())

    localize_metadata_schema(metadata)

    with open(metadata_file, "w") as fout:
        yaml_handler.dump(metadata, fout)


def change_zip_file(charm_name, metadata, charm_path="."):
    """Inject the modified metadata into a built charm."""
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


def main(metadata_path="./metadata.yaml"):
    """Given a metadata file, localize any remote schema references in place."""
    localize_metadata_file(metadata_path)


if __name__ == "__main__":
    typer.run(main)
