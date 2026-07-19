"""Shared deterministic serialization helpers for document wire models."""

from __future__ import annotations

from io import StringIO

from frontmatter_format import new_yaml

_CLEAN_YAML_WIDTH = 4096
"""Prevent ordinary scalar wrapping from introducing trailing whitespace."""


def _is_empty(value: object) -> bool:
    return value is None or value == {} or value == []


def clean_yaml(value: object) -> str:
    """
    Dump a plain value to deterministic block-style YAML with multiline block scalars,
    field order preserved, and null or empty values suppressed.
    """
    stream = StringIO()
    yaml = new_yaml(suppress_vals=_is_empty, typ="rt")
    yaml.width = _CLEAN_YAML_WIDTH
    yaml.dump(value, stream)
    return stream.getvalue()
