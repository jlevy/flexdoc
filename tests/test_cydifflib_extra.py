from __future__ import annotations

import subprocess
import sys
from importlib.metadata import requires
from unittest.mock import patch

import pytest

from flexdoc.docs.token_diffs import MISSING_CYDIFFLIB_ERROR, diff_wordtoks


def test_cydifflib_is_diff_extra_not_hard_dependency() -> None:
    reqs = requires("flexdoc") or []
    cydiff_reqs = [req for req in reqs if req.startswith("cydifflib")]
    assert cydiff_reqs
    assert all("extra == 'diff'" in req or 'extra == "diff"' in req for req in cydiff_reqs)


def test_missing_cydifflib_names_diff_extra() -> None:
    with patch(
        "flexdoc.docs.token_diffs.importlib.import_module",
        side_effect=ImportError("No module named 'cydifflib'"),
    ):
        with pytest.raises(ImportError, match=r"flexdoc\[diff\]") as err:
            diff_wordtoks(["a"], ["b"])
    assert str(err.value) == MISSING_CYDIFFLIB_ERROR


def test_import_flexdoc_does_not_load_cydifflib() -> None:
    script = (
        "import sys\nimport flexdoc\nimport flexdoc.html\nassert 'cydifflib' not in sys.modules\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
