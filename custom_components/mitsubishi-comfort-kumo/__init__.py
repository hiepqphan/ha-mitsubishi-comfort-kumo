from datetime import timedelta
import logging, asyncio, traceback
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .kumo_api import KumoCloudClient

_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[Platform] = [Platform.SENSOR]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up My Cloud Device from a config entry."""
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    
    # Initialize your API kumo_ using username/password here
    kumo_client = await hass.async_add_executor_job(
        KumoCloudClient, username, password
    )
    await hass.async_add_executor_job(kumo_client.login)
    # kumo_client.login(username, password)
    await asyncio.sleep(3)
    await hass.async_add_executor_job(kumo_client._load_first_site_id)
    # kumo_client._load_first_site_id()
    await asyncio.sleep(3)
    await hass.async_add_executor_job(kumo_client._load_device_serials)
    # kumo_client._load_device_serials()

    async def async_update_data():
        """Fetch data from cloud API endpoint."""
        try:
            result = {"temperature": 0}
            # Replace with your actual cloud async fetch call
            # Refresh data read
            if kumo_client.device_serials is not None and len(kumo_client.device_serials) > 0:
                device_status = await hass.async_add_executor_job(
                    kumo_client.get_fresh_device_status,
                    kumo_client.device_serials[0].get("adapter").get("deviceSerial")
                )
                result.get("temperature") = device_status.get("roomTemp")
            else:
                _LOGGER.debug("Kumo client has no device serials")
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
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
