"""Data coordinator for OpenSenseMap integration."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Any

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    API_URL,
    CONF_ACCESS_TOKEN,
    CONF_BOX_ID,
    CONF_DEBUG_MODE,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    MEASUREMENT_HUMIDITY,
    MEASUREMENT_PRESSURE,
    MEASUREMENT_TEMPERATURE,
    SENSOR_CONFIGS,
    SOFTWARE_TYPE,
)

_LOGGER = logging.getLogger(__name__)

HTTP_TIMEOUT = 30


class OpenSenseMapCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for pushing data to OpenSenseMap API."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        self._box_id = entry.data[CONF_BOX_ID]
        self._access_token = entry.data.get(CONF_ACCESS_TOKEN)
        self._session: aiohttp.ClientSession | None = None

        # Status tracking
        self.last_upload: datetime | None = None
        self.last_error: str | None = None
        self.upload_count: int = 0
        self.last_request_data: dict[str, Any] | None = None

        # Get update interval
        interval = entry.options.get(
            CONF_UPDATE_INTERVAL,
            entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=interval),
        )

    @property
    def debug_mode(self) -> bool:
        """Return whether debug mode is enabled."""
        return self.entry.options.get(
            CONF_DEBUG_MODE,
            self.entry.data.get(CONF_DEBUG_MODE, False),
        )

    @property
    def next_upload(self) -> datetime | None:
        """Return the next scheduled upload time."""
        if self.last_upload:
            return self.last_upload + self.update_interval
        return None

    def _all_sensors_available(self) -> tuple[bool, list[str]]:
        """Check if all configured sensors are available.

        Returns a tuple of (all_available, list_of_unavailable_entities).
        """
        config_data = self.entry.data
        options = self.entry.options
        unavailable: list[str] = []

        for sensor_id_key, entity_key, label, measurement_type in SENSOR_CONFIGS:
            sensor_id = options.get(sensor_id_key, config_data.get(sensor_id_key))
            entity_id = options.get(entity_key, config_data.get(entity_key))

            # Only check entities that are actually configured
            if not sensor_id or not entity_id:
                continue

            state = self.hass.states.get(entity_id)
            if state is None or state.state in ("unknown", "unavailable", None):
                unavailable.append(entity_id)

        return len(unavailable) == 0, unavailable

    async def _async_update_data(self) -> dict[str, Any]:
        """Push sensor data to OpenSenseMap API."""
        try:
            # Check if all configured sensors are available
            all_available, unavailable = self._all_sensors_available()
            if not all_available:
                self.last_error = f"Sensors unavailable: {', '.join(unavailable)}"
                _LOGGER.warning(
                    "Skipping OpenSenseMap upload - sensors unavailable: %s",
                    unavailable,
                )
                return self._get_status_data()

            if self._session is None:
                self._session = aiohttp.ClientSession()

            success, response = await self._push_sensor_data()

            if success:
                self.last_upload = datetime.now()
                self.upload_count += 1
                self.last_error = None
            else:
                self.last_error = response or "Unknown error"

            return self._get_status_data()

        except Exception as err:
            self.last_error = str(err)
            _LOGGER.exception("Error pushing data to OpenSenseMap")
            return self._get_status_data()

    async def _push_sensor_data(self) -> tuple[bool, str | None]:
        """Push sensor data to the API."""
        # Collect sensor values
        sensor_data = self._collect_sensor_data()

        if not sensor_data:
            _LOGGER.debug("No sensor data to push")
            return True, None  # Consider it success if nothing to push

        # Build URL
        url = API_URL.format(box_id=self._box_id)

        # Build headers
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": f"{SOFTWARE_TYPE}/1.0.0",
        }

        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"

        if self.debug_mode:
            self.last_request_data = {
                "url": url,
                "headers": {k: v if k != "Authorization" else "***" for k, v in headers.items()},
                "payload": sensor_data,
            }
            _LOGGER.debug(
                "Pushing data to OpenSenseMap: %s",
                self.last_request_data,
            )

        try:
            async with asyncio.timeout(HTTP_TIMEOUT):
                async with self._session.post(
                    url,
                    json=sensor_data,
                    headers=headers,
                ) as response:
                    if response.status in (200, 201):
                        _LOGGER.debug("Successfully pushed data to OpenSenseMap")
                        return True, None
                    else:
                        error_text = await response.text()
                        _LOGGER.error(
                            "Failed to push data to OpenSenseMap: %s - %s",
                            response.status,
                            error_text,
                        )
                        return False, f"HTTP {response.status}: {error_text}"

        except asyncio.TimeoutError:
            _LOGGER.error("Timeout pushing data to OpenSenseMap")
            return False, "Request timeout"
        except aiohttp.ClientError as err:
            _LOGGER.error("Network error pushing data to OpenSenseMap: %s", err)
            return False, str(err)

    def _collect_sensor_data(self) -> dict[str, str]:
        """Collect sensor data values from Home Assistant entities."""
        data: dict[str, str] = {}
        config_data = self.entry.data
        options = self.entry.options

        for sensor_id_key, entity_key, label, measurement_type in SENSOR_CONFIGS:
            # Get sensor ID and entity ID from options first, then data
            sensor_id = options.get(sensor_id_key, config_data.get(sensor_id_key))
            entity_id = options.get(entity_key, config_data.get(entity_key))

            if not sensor_id or not entity_id:
                continue

            state = self.hass.states.get(entity_id)
            if state is None or state.state in ("unknown", "unavailable", None):
                _LOGGER.debug("Skipping %s: state is %s", entity_id, state)
                continue

            try:
                value = float(state.state)

                # Apply unit conversions based on measurement type
                value = self._convert_value(measurement_type, value, state)

                data[sensor_id] = f"{value:.2f}"

            except (ValueError, TypeError) as err:
                _LOGGER.debug("Could not convert %s value: %s", entity_id, err)

        return data

    def _convert_value(self, measurement_type: str, value: float, state: Any) -> float:
        """Convert sensor value to the required unit."""
        unit = state.attributes.get("unit_of_measurement", "")

        # Temperature: convert Fahrenheit to Celsius
        if measurement_type == MEASUREMENT_TEMPERATURE:
            if unit in ("°F", "F"):
                value = (value - 32) * 5 / 9
                _LOGGER.debug("Converted temperature from °F to °C: %.2f", value)

        # Pressure: convert to Pa
        elif measurement_type == MEASUREMENT_PRESSURE:
            if unit in ("hPa", "mbar", ""):
                value = value * 100
                _LOGGER.debug("Converted pressure from hPa to Pa: %.2f", value)
            elif unit == "inHg":
                value = value * 3386.39
                _LOGGER.debug("Converted pressure from inHg to Pa: %.2f", value)
            elif unit == "psi":
                value = value * 6894.76
                _LOGGER.debug("Converted pressure from psi to Pa: %.2f", value)
            # If already in Pa, no conversion needed

        # Humidity: ensure percentage (0-100)
        elif measurement_type == MEASUREMENT_HUMIDITY:
            if value > 1 and value <= 100:
                pass  # Already in percentage
            elif value <= 1:
                value = value * 100  # Convert from decimal to percentage
                _LOGGER.debug("Converted humidity from decimal to percentage: %.2f", value)

        return value

    def _get_status_data(self) -> dict[str, Any]:
        """Get status data for the sensor."""
        data: dict[str, Any] = {
            "last_upload": self.last_upload.isoformat() if self.last_upload else None,
            "last_error": self.last_error,
            "upload_count": self.upload_count,
            "next_upload": self.next_upload.isoformat() if self.next_upload else None,
            "box_id": self._box_id,
        }

        if self.debug_mode and self.last_request_data:
            data["last_request"] = self.last_request_data

        return data

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator and close the session."""
        if self._session:
            await self._session.close()
            self._session = None
