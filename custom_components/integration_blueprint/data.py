"""Custom types for integration_blueprint."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration

    from .api import IntegrationEnerga24HacsApiClient
    from .coordinator import BlueprintDataUpdateCoordinator


type IntegrationEnerga24HacsConfigEntry = ConfigEntry[IntegrationEnerga24HacsData]


@dataclass
class IntegrationEnerga24HacsData:
    """Data for the Blueprint integration."""

    client: IntegrationEnerga24HacsApiClient
    coordinator: BlueprintDataUpdateCoordinator
    integration: Integration
