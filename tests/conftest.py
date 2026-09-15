"""Gemeinsame Vorrichtungen der Tests."""

from __future__ import annotations

import pytest

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Ohne diese Vorrichtung laedt Home Assistant eigene Integrationen nicht."""
    yield
