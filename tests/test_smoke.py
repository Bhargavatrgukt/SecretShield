"""Smoke test: proves the project is installed and pytest can find it."""

import secretshield


def test_package_imports_and_has_version():
    assert secretshield.__version__ == "0.1.0"
