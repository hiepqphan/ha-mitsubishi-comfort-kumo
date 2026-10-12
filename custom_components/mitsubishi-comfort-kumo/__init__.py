from datetime import timedelta
from typing import Any
import logging, asyncio, traceback
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .kumo_api import KumoCloudClient

_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[Platform] = [Platform.CLIMATE]

def _get_temperature(device: Any) -> float:
    adapter = device.get("adapter")
    cool_temp = adapter.get("spCool")
    heat_temp = adapter.get("spHeat")
    mode = adapter.get("operationMode")
    if mode != "cool" and mode != "heat":
        mode = adapter.get("previousOperationMode")
    if mode == "cool": return cool_temp
    elif mode == "heat": return heat_temp
    else: return 0.0


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up My Cloud Device from a config entry."""
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    
    # Initialize your API kumo_ using username/password here
    kumo_client = await hass.async_add_executor_job(
        KumoCloudClient, username, password
    )

    async def async_update_data():
        """Fetch data from cloud API endpoint."""
        try:
            result = {}
            # Replace with your actual cloud async fetch call
            # Refresh data read
            # Login and load devices
            await hass.async_add_executor_job(kumo_client.login_and_fetch_devices)
            for device in kumo_client.devices:
                result[device.get("adapter").get("deviceSerial")] = {
                    "name": device.get("name"),
                    "room_temp": device.get("adapter").get("roomTemp"),
                    "set_temp": _get_temperature(device),
                    "mode": device.get("operationMode")
                }
            return result
        except Exception as err:
            _LOGGER.error("kumo failed here: %s", traceback.format_exc())
            _LOGGER.error("kumo failed error: %s", err)
            raise UpdateFailed(f"Cloud communication error: {err}")

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=async_update_data,
        update_interval=timedelta(seconds=60),
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
    return unload_ok
