"""Config flow for IntesisHome."""
import logging

from pyintesishome import IHAuthenticationError, IHConnectionError, IntesisHome
from pyintesishome.const import DEVICE_INTESISHOME
import voluptuous as vol

from homeassistant import config_entries, exceptions
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)


class IntesisConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for IntesisHome."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        """Handle username / password entry."""
        errors: dict[str, str] = {}

        schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )

        if user_input:
            controller = IntesisHome(
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
                self.hass.loop,
                websession=async_get_clientsession(self.hass),
                device_type=DEVICE_INTESISHOME,
            )
            try:
                await controller.poll_status()

                if not controller.get_devices():
                    errors["base"] = "no_devices"
                else:
                    unique_id = (
                        f"{controller.device_type}_{controller.controller_id}".lower()
                    )
                    await self.async_set_unique_id(unique_id)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=controller.name or "IntesisHome",
                        data={
                            CONF_USERNAME: user_input[CONF_USERNAME],
                            CONF_PASSWORD: user_input[CONF_PASSWORD],
                        },
                    )

            except IHAuthenticationError:
                errors["base"] = "invalid_auth"
            except IHConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during config flow")
                errors["base"] = "unknown"
            finally:
                await controller.stop()

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_import(self, import_data) -> ConfigFlowResult:
        """Handle YAML import."""
        return await self.async_step_user(import_data)


class CannotConnect(exceptions.HomeAssistantError):
    """Cannot connect to IntesisHome."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Invalid credentials."""


class NoDevices(exceptions.HomeAssistantError):
    """No devices found on account."""
