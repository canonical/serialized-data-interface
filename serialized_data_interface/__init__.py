# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

# flake8: noqa: ignore=F401
# type: ignore

# Direct imports for namespaced references.
from . import errors, relation, testing

# Top-level imports for direct import.
# (Prefer referencing errors via module, but keep these for compatibility.)
from .errors import (
    InvalidRelationName,
    NoCompatibleVersions,
    NoSchemaDefined,
    NoVersionsListed,
)
from .relation import EndpointWrapper
from .sdi import SerializedDataInterface, get_interface, get_interfaces
from .testing import MockRemoteRelationMixin
