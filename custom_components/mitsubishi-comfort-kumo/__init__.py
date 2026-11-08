import voluptuous as vol
from datetime import timedelta
from typing import Any
import logging, asyncio, traceback
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, ATTR_TEMPERATURE, Platform
from homeassistant.helpers import config_validation as cv
from homeassistant.components.climate import HVACMode
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    HA_TO_KUMO_MODE,
    POLL_INTERVAL_SECONDS,
)
from .kumo_api import KumoCloudClient

_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[Platform] = [Platform.CLIMATE]
SET_ALL_MINISPLITS_SERVICE_NAME = "set_all_minisplits"
SET_ALL_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Optional("mode"): vol.In([HVACMode.COOL, HVACMode.HEAT, HVACMode.OFF]),
        vol.Optional(ATTR_TEMPERATURE): cv.positive_int,
    }
)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up My Cloud Device from a config entry."""
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]

    # Initialize your API using username/password here
    kumo_client = await hass.async_add_executor_job(
        KumoCloudClient, username, password
    )
    await hass.async_add_executor_job(kumo_client.login_and_fetch_devices,
                                      _LOGGER)

    _LOGGER.info("Successfully initialized Kumo Client.")

    async def async_update_data():
        """Fetch data from cloud API endpoint."""
        try:
            result = {}
            # Replace with your actual cloud async fetch call
            # Refresh data read
            devices = await hass.async_add_executor_job(kumo_client.get_all_devices,
                                                        kumo_client.site_id,
                                                        True,
                                                        True)
            _LOGGER.info("Refreshed devices' status.")
            for device in devices:
                result[device.serial] = {
                    "name": device.name,
                    "room_temp": device.room_temp,
                    "set_temp": device.set_temp,
                    "mode": device.mode,
                }
            return result
        except Exception as err:
            await hass.async_add_executor_job(kumo_client.login_and_fetch_devices)
            raise UpdateFailed(f"Cloud communication error: {err}")

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=async_update_data,
        update_interval=timedelta(seconds=POLL_INTERVAL_SECONDS),
    )

    async def handle_set_all_minisplits(call: ServiceCall) -> None:
        """Service handler to broadcast commands to all units."""
        target_mode = call.data.get("mode")
        target_temp = call.data.get(ATTR_TEMPERATURE)

        # Get all splits currently managed by your integration cache
        if not coordinator.data:
            return

        # Loop through every split ID and fire requests asynchronously in parallel

        for device_id in coordinator.data.keys():
            if target_mode:
                await hass.async_add_executor_job(
                    kumo_client.send_device_command,
                    device_id,
                    {"operationMode": HA_TO_KUMO_MODE[target_mode]},
                )
            # This is takes raw input number, and Mitsubishi uses Celsius
            if target_temp:
                kumo_mode = coordinator.data[device_id].get("mode")
                temperature_field = kumo_client.get_temperature_field(kumo_mode)
                if temperature_field == None:
                    return
                await hass.async_add_executor_job(
                    kumo_client.send_device_command,
                    device_id,
                    {temperature_field: target_temp},
                )

        # Force a refresh so all UI cards update instantly
        await coordinator.async_request_refresh()

    # Register the service action into Home Assistant
    hass.services.async_register(
        DOMAIN,
        SET_ALL_MINISPLITS_SERVICE_NAME,
        handle_set_all_minisplits,
        schema=SET_ALL_SERVICE_SCHEMA,
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    hass.data[DOMAIN][entry.entry_id + "_kumo_client"] = kumo_client
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        hass.services.async_remove(DOMAIN, SET_ALL_MINISPLITS_SERVICE_NAME)
    return unload_ok
