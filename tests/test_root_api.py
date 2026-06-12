"""
Contract for the package-root API surface. The root surface grows only deliberately
(see the root-surface definition task in the extraction plan), so this pins both the
identity of the entry point and the exact set of root exports.
"""

from __future__ import annotations

import flexdoc
import flexdoc.docs


def test_root_flexdoc_is_the_canonical_class():
    assert flexdoc.FlexDoc is flexdoc.docs.FlexDoc
    doc = flexdoc.FlexDoc.from_text("# T\n\nBody.\n")
    assert doc.reassemble()


def test_root_surface_is_deliberate():
    assert flexdoc.__all__ == ["FlexDoc"]
