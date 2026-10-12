import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, HA_TO_KUMO_MODE, KUMO_TO_HA_MODE

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Kumo Climate entities from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    # Dynamically generate an entity for each minisplit key in your cloud payload
    entities = []
    if coordinator.data:
        for id, device in coordinator.data.items():
            entities.append(MitsubishiMinisplit(coordinator, entry, id, device.get("name")))

    async_add_entities(entities)


class MitsubishiMinisplit(CoordinatorEntity, ClimateEntity):
    """Representation of a Mitsubishi Kumo Minisplit unit."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.COOL, HVACMode.HEAT, HVACMode.OFF, HVACMode.DRY, HVACMode.FAN_ONLY, HVACMode.AUTO]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE 
        | ClimateEntityFeature.TURN_ON 
        | ClimateEntityFeature.TURN_OFF
    )

    def __init__(self, coordinator, entry: ConfigEntry, device_id: str, name: str) -> None:
        """Initialize the climate entity."""
        super().__init__(coordinator)
        self.entry = entry
        self.device_id = device_id
        
        # Entity Identifiers
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{device_id}_climate"

        # Unique Device container per minisplit unit
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_{device_id}")},
            name=name,
            manufacturer="Mitsubishi",
            model="MSZ-FX",
        )

    @property
    def _device_data(self) -> dict[str, Any]:
        """Helper to get data safely for this specific minisplit from cache."""
        return self.coordinator.data.get(self.device_id, {}) if self.coordinator.data else {}

    @property
    def current_temperature(self) -> float | None:
        """Return the current room temperature."""
        return self._device_data.get("room_temp")

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we want to set."""
        return self._device_data.get("set_temp")

    @property
    def hvac_mode(self) -> HVACMode | None:
        """Return current hvac operation ie. heat, cool, off."""
        kumo_mode = self._device_data.get("mode")
        return KUMO_TO_HA_MODE.get(kumo_mode, HVACMode.OFF)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode via Cloud API."""
        kumo_mode = HA_TO_KUMO_MODE.get(hvac_mode, "off")
        
        # Pull your cloud api client wrapper context
        # Adjust this call to your actual kumo_api method signature
        kumo_client = self.coordinator.hass.data[DOMAIN][self.entry.entry_id + "_kumo_client"]
        
        # Execute blocking cloud command in executor
        await self.hass.async_add_executor_job(
            kumo_client.send_device_command, self.device_id, {
                "operationMode": kumo_mode
            }
        )

        # If updating master unit, change all other units (if not ignored)
        if self.device_id == kumo_client.master_unit_serial:
            for id, device in self.coordinator.data.items():
                if id == self.device_id or id in kumo_client.ignored_unit_serials:
                    continue
                await self.hass.async_add_executor_job(
                    kumo_client.send_device_command, id, {
                        "operationMode": kumo_mode
                    }
                )
        
        # Force a background data refresh so the UI updates instantly
        await self.coordinator.async_request_refresh()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature via Cloud API."""
        if (target_temp := kwargs.get(ATTR_TEMPERATURE)) is None:
            return

        kumo_client = self.coordinator.hass.data[DOMAIN][self.entry.entry_id + "_kumo_client"]
        
        # Execute blocking cloud command in executor
        kumo_mode = self.coordinator.data[self.device_id].get("mode")
        temperature_field = ""
        if kumo_mode == "heat": temperature_field = "spHeat"
        elif kumo_mode == "cool": temperature_field = "spCool"
        else: return
        await self.hass.async_add_executor_job(
            kumo_client.send_device_command, self.device_id, {
                temperature_field: target_temp
            }
        )

        # If updating master unit, change all other units (if not ignored)
        if self.device_id == kumo_client.master_unit_serial:
            for id, device in self.coordinator.data.items():
                if id == self.device_id or id in kumo_client.ignored_unit_serials:
                    continue
                await self.hass.async_add_executor_job(
                    kumo_client.send_device_command, id, {
                        temperature_field: target_temp
                    }
                )
        
        # Force a background data refresh so the UI updates instantly
        await self.coordinator.async_request_refresh()
