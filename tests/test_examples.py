from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_EXAMPLES = [
    _REPO_ROOT / "examples" / "doc_structure.py",
    _REPO_ROOT / "examples" / "normalized_form.py",
    _REPO_ROOT / "examples" / "backfill_timestamps.py",
]


def test_examples_run_from_checkout() -> None:
    for script in _EXAMPLES:
        result = subprocess.run(
            [sys.executable, str(script)],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr + result.stdout
