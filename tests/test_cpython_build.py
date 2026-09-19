from __future__ import annotations

from unittest.mock import patch

import pytest

from flexdoc.util.cpython_build import (
    FREETHREADED_CPYTHON_ERROR,
    is_gil_disabled_build,
    require_gil_cpython,
)


def test_is_gil_disabled_build_false_on_gil_runner() -> None:
    assert is_gil_disabled_build() is False


def test_is_gil_disabled_build_true_when_config_var_mocked() -> None:
    with patch("flexdoc.util.cpython_build.sysconfig.get_config_var", return_value=1):
        assert is_gil_disabled_build() is True


def test_require_gil_cpython_ok_on_gil_runner() -> None:
    require_gil_cpython()


def test_require_gil_cpython_raises_when_config_var_mocked() -> None:
    with patch("flexdoc.util.cpython_build.sysconfig.get_config_var", return_value=1):
        with pytest.raises(RuntimeError, match="3.14t"):
            require_gil_cpython()


def test_require_gil_cpython_error_names_uv_interpreter_trap() -> None:
    with patch("flexdoc.util.cpython_build.sysconfig.get_config_var", return_value=1):
        with pytest.raises(RuntimeError) as err:
            require_gil_cpython()
    assert str(err.value) == FREETHREADED_CPYTHON_ERROR
