from __future__ import annotations

import sysconfig

FREETHREADED_CPYTHON_ERROR = (
    "flexdoc supports CPython 3.11–3.14 with the GIL, not free-threaded CPython "
    "(3.14t). Use --python 3.13 or a GIL 3.14 interpreter. "
    "`uv python find 3.14` may resolve to 3.14t."
)


def is_gil_disabled_build() -> bool:
    """
    True when this CPython was built with the GIL disabled (`3.13t` / `3.14t`).

    Uses the `Py_GIL_DISABLED` build flag, not live GIL state. Importing
    `cydifflib` on 3.14t re-enables the GIL, so `sys._is_gil_enabled()` after
    that import is a lie.
    """
    return sysconfig.get_config_var("Py_GIL_DISABLED") == 1


def require_gil_cpython() -> None:
    """Refuse free-threaded CPython before importing `cydifflib`."""
    if is_gil_disabled_build():
        raise RuntimeError(FREETHREADED_CPYTHON_ERROR)
