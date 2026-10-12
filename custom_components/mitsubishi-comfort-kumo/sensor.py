import logging
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Kumo Cloud sensor platform from a config entry."""
    # Retrieve the central data coordinator created in __init__.py
    coordinator = hass.data[DOMAIN][entry.entry_id]

    # Assume your API returns a dictionary of devices or a single payload.
    # For this example, we generate one temperature sensor.
    async_add_entities([KumoTemperatureSensor(coordinator, entry)])


class KumoTemperatureSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Kumo Cloud Temperature Sensor."""

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        # Connects this entity directly to the coordinator's refresh loop
        super().__init__(coordinator)
        self.entry = entry

        # Define basic entity properties
        self._attr_name = "Kumo Room Temperature"
        self._attr_unique_id = f"{entry.entry_id}_room_temp"
        
        # Configure standard Home Assistant physics properties
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

        # Group this sensor under a neat Device UI container in Home Assistant
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Mitsubishi Minisplit",
            manufacturer="Mitsubishi",
            model="Kumo Cloud Adapter",
        )

    @property
    def native_value(self):
        """Return the state of the sensor directly from coordinator cache."""
        if self.coordinator.data is None:
            return None
            
        # Adjust the key below ("temperature") to match the exact key 
        # returned by your kumo_api.py status dictionary.
        return self.coordinator.data.get("temperature")

    @property
    def available(self) -> bool:
        """Return if the sensor is legally online based on last cloud fetch."""
        return self.coordinator.last_update_success
