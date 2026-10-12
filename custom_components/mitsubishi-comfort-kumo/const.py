from homeassistant.components.climate import HVACMode

DOMAIN = "mitsubishi_comfort_kumo"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"

# Map Home Assistant HVAC modes to whatever your kumo_api expects
HA_TO_KUMO_MODE = {
    HVACMode.COOL: "cool",
    HVACMode.HEAT: "heat",
    HVACMode.OFF: "off",
    HVACMode.DRY: "dry",
    HVACMode.FAN_ONLY: "vent",
    HVACMode.AUTO: "auto"
}
KUMO_TO_HA_MODE = {v: k for k, v in HA_TO_KUMO_MODE.items()}