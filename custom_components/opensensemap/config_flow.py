"""Config flow for OpenSenseMap integration."""
from __future__ import annotations

import logging
import re
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    ALL_ENTITY_KEYS,
    ALL_SENSOR_ID_KEYS,
    CONF_ACCESS_TOKEN,
    CONF_BOX_ID,
    CONF_DEBUG_MODE,
    CONF_ENTITY_HUMIDITY,
    CONF_ENTITY_PM10,
    CONF_ENTITY_PM25,
    CONF_ENTITY_PRESSURE,
    CONF_ENTITY_TEMPERATURE,
    CONF_SENSOR_ID_HUMIDITY,
    CONF_SENSOR_ID_PM10,
    CONF_SENSOR_ID_PM25,
    CONF_SENSOR_ID_PRESSURE,
    CONF_SENSOR_ID_TEMPERATURE,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    MIN_UPDATE_INTERVAL,
    SENSOR_CONFIGS,
)

_LOGGER = logging.getLogger(__name__)

# OpenSenseMap box IDs are 24-character hex strings
BOX_ID_PATTERN = re.compile(r"^[a-fA-F0-9]{24}$")
# Sensor IDs are also 24-character hex strings
SENSOR_ID_PATTERN = re.compile(r"^[a-fA-F0-9]{24}$")


def validate_box_id(box_id: str) -> bool:
    """Validate the box ID format."""
    return bool(BOX_ID_PATTERN.match(box_id))


def validate_sensor_id(sensor_id: str) -> bool:
    """Validate the sensor ID format."""
    return bool(SENSOR_ID_PATTERN.match(sensor_id))


class OpenSenseMapConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for OpenSenseMap."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - box configuration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            box_id = user_input[CONF_BOX_ID].strip()
            access_token = user_input.get(CONF_ACCESS_TOKEN, "").strip()

            if not validate_box_id(box_id):
                errors["base"] = "invalid_box_id"
            else:
                # Check if already configured
                await self.async_set_unique_id(box_id)
                self._abort_if_unique_id_configured()

                self._data[CONF_BOX_ID] = box_id
                if access_token:
                    self._data[CONF_ACCESS_TOKEN] = access_token

                return await self.async_step_sensors()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_BOX_ID): str,
                    vol.Optional(CONF_ACCESS_TOKEN): str,
                }
            ),
            errors=errors,
        )

    async def async_step_sensors(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle sensor mapping step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Check that at least one pair is configured
            has_valid_pair = False

            for sensor_id_key, entity_key, label, _ in SENSOR_CONFIGS:
                sensor_id = user_input.get(sensor_id_key, "").strip()
                entity_id = user_input.get(entity_key)

                if sensor_id and entity_id:
                    has_valid_pair = True
                    self._data[sensor_id_key] = sensor_id
                    self._data[entity_key] = entity_id
                elif sensor_id or entity_id:
                    # Only one of the pair is configured
                    errors["base"] = "incomplete_sensor_pair"

            if not has_valid_pair and "base" not in errors:
                errors["base"] = "no_sensor_configured"

            if not errors:
                return await self.async_step_options()

        return self.async_show_form(
            step_id="sensors",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_ENTITY_PM25): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="sensor")
                    ),
                    vol.Optional(CONF_SENSOR_ID_PM25): str,
                    vol.Optional(CONF_ENTITY_PM10): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="sensor")
                    ),
                    vol.Optional(CONF_SENSOR_ID_PM10): str,
                    vol.Optional(CONF_ENTITY_TEMPERATURE): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="sensor")
                    ),
                    vol.Optional(CONF_SENSOR_ID_TEMPERATURE): str,
                    vol.Optional(CONF_ENTITY_HUMIDITY): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="sensor")
                    ),
                    vol.Optional(CONF_SENSOR_ID_HUMIDITY): str,
                    vol.Optional(CONF_ENTITY_PRESSURE): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="sensor")
                    ),
                    vol.Optional(CONF_SENSOR_ID_PRESSURE): str,
                }
            ),
            errors=errors,
        )

    async def async_step_options(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle options configuration step."""
        if user_input is not None:
            self._data[CONF_UPDATE_INTERVAL] = user_input.get(
                CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
            )
            self._data[CONF_DEBUG_MODE] = user_input.get(CONF_DEBUG_MODE, False)

            return self.async_create_entry(
                title=f"OpenSenseMap ({self._data[CONF_BOX_ID][:8]}...)",
                data=self._data,
            )

        return self.async_show_form(
            step_id="options",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_UPDATE_INTERVAL,
                        default=DEFAULT_UPDATE_INTERVAL,
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=MIN_UPDATE_INTERVAL,
                            max=3600,
                            step=60,
                            unit_of_measurement="seconds",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Optional(CONF_DEBUG_MODE, default=False): bool,
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> OpenSenseMapOptionsFlow:
        """Get the options flow for this handler."""
        return OpenSenseMapOptionsFlow()


class OpenSenseMapOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for OpenSenseMap."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle options flow."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Store sensor mappings
            valid_data: dict[str, Any] = {}
            has_valid_pair = False

            for sensor_id_key, entity_key, label, _ in SENSOR_CONFIGS:
                sensor_id = user_input.get(sensor_id_key, "").strip() if user_input.get(sensor_id_key) else ""
                entity_id = user_input.get(entity_key)

                if sensor_id and entity_id:
                    has_valid_pair = True
                    valid_data[sensor_id_key] = sensor_id
                    valid_data[entity_key] = entity_id

            if not has_valid_pair:
                errors["base"] = "no_sensor_configured"
            else:
                valid_data[CONF_UPDATE_INTERVAL] = user_input.get(
                    CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
                )
                valid_data[CONF_DEBUG_MODE] = user_input.get(CONF_DEBUG_MODE, False)
                return self.async_create_entry(title="", data=valid_data)

        # Get current values - merge data and options
        current_data = {**self.config_entry.data, **self.config_entry.options}

        # Create entity selector
        entity_selector = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )

        schema_dict: dict[vol.Marker, Any] = {}

        for sensor_id_key, entity_key, label, _ in SENSOR_CONFIGS:
            current_sensor_id = current_data.get(sensor_id_key, "")
            current_entity = current_data.get(entity_key)

            schema_dict[vol.Optional(
                entity_key,
                description={"suggested_value": current_entity},
            )] = entity_selector
            schema_dict[vol.Optional(
                sensor_id_key,
                description={"suggested_value": current_sensor_id},
            )] = str

        current_interval = current_data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        current_debug = current_data.get(CONF_DEBUG_MODE, False)

        schema_dict[vol.Optional(
            CONF_UPDATE_INTERVAL,
            default=current_interval,
        )] = selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=MIN_UPDATE_INTERVAL,
                max=3600,
                step=60,
                unit_of_measurement="seconds",
                mode=selector.NumberSelectorMode.BOX,
            )
        )
        schema_dict[vol.Optional(CONF_DEBUG_MODE, default=current_debug)] = bool

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
        )
