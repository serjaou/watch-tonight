"""Smoke test to verify the package imports and test runner works."""

import watch_tonight


def test_package_imports() -> None:
    assert watch_tonight.__doc__ is not None
