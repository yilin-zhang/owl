from __future__ import annotations

import re

from owl_cli.utils import utc_now


def test_timestamps_include_subsecond_precision() -> None:
    assert re.search(r"\.\d{6}Z$", utc_now())
