import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, CONF_IGNORED_UNITS_SERIALS, CONF_MASTER_UNIT_SERIAL
from .kumo_api import KumoCloudClient

_LOGGER = logging.getLogger(__name__)


class MyCloudDeviceConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for My Cloud Device."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step asking for credentials."""
        errors = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]

            # API validation function here
            # e.g., success = await async_validate_credentials(username, password)
            client = KumoCloudClient(username, password)
            login_result = client.login()
            success = (
                login_result.get("email") is not None
                and login_result.get("email") != ""
            )

            if success:
                # Creates the integration instance in HA
                return self.async_create_entry(title=username, data=user_input)
            else:
                errors["base"] = "invalid_auth"

        # Define the UI form fields
        data_schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Optional(CONF_MASTER_UNIT_SERIAL, "", ""): cv.string,
                vol.Optional(
                    CONF_IGNORED_UNITS_SERIALS, "comma sep list", ""
                ): cv.string,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )
