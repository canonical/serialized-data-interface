# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.
try:
    from functools import cache  # type: ignore
except ImportError:
    # create shim for functools.cache in 3.8
    from functools import lru_cache

    cache = lru_cache(maxsize=None)
