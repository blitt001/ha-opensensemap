"""Sensor platform for OpenSenseMap integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_BOX_ID, DOMAIN
from .coordinator import OpenSenseMapCoordinator

# Status options for the enum sensor
STATUS_PENDING = "pending"
STATUS_OK = "ok"
STATUS_ERROR = "error"
STATUS_OPTIONS = [STATUS_PENDING, STATUS_OK, STATUS_ERROR]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up OpenSenseMap sensor from a config entry."""
    coordinator: OpenSenseMapCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([OpenSenseMapStatusSensor(coordinator, entry)])


class OpenSenseMapStatusSensor(
    CoordinatorEntity[OpenSenseMapCoordinator], SensorEntity
):
    """Sensor representing the OpenSenseMap upload status."""

    entity_description = SensorEntityDescription(
        key="status",
        translation_key="status",
        icon="mdi:cloud-upload",
        device_class=SensorDeviceClass.ENUM,
    )

    _attr_has_entity_name = True
    _attr_options = STATUS_OPTIONS

    def __init__(
        self,
        coordinator: OpenSenseMapCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._box_id = entry.data[CONF_BOX_ID]

        self._attr_unique_id = f"{entry.entry_id}_status"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"OpenSenseMap ({self._box_id[:8]}...)",
            manufacturer="OpenSenseMap",
            model="SenseBox",
            sw_version="1.0.0",
        )

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        if self.coordinator.last_error:
            return STATUS_ERROR
        elif self.coordinator.last_upload:
            return STATUS_OK
        else:
            return STATUS_PENDING

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attrs: dict[str, Any] = {
            "box_id": self._box_id,
            "upload_count": self.coordinator.upload_count,
        }

        if self.coordinator.last_upload:
            attrs["last_upload"] = self.coordinator.last_upload.isoformat()

        if self.coordinator.next_upload:
            attrs["next_upload"] = self.coordinator.next_upload.isoformat()

        if self.coordinator.last_error:
            attrs["last_error"] = self.coordinator.last_error

        if self.coordinator.debug_mode and self.coordinator.last_request_data:
            attrs["last_request"] = self.coordinator.last_request_data

        return attrs

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return True  # Always available, shows error state if there are issues
