"""Config flow for IntesisHome."""
from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

from pyintesishome import IHAuthenticationError, IHConnectionError, IntesisHome
from pyintesishome.const import DEVICE_INTESISHOME
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)


class IntesisConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for IntesisHome."""

    VERSION = 1

    async def _async_validate(
        self, username: str, password: str
    ) -> tuple[IntesisHome, str | None]:
        """Validate credentials.

        Returns the controller (which the caller MUST stop) and an error key,
        or ``None`` when validation succeeds.
        """
        controller = IntesisHome(
            username,
            password,
            self.hass.loop,
            websession=async_get_clientsession(self.hass),
            device_type=DEVICE_INTESISHOME,
        )
        try:
            await controller.poll_status()
        except IHAuthenticationError:
            return controller, "invalid_auth"
        except IHConnectionError:
            return controller, "cannot_connect"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception during config flow")
            return controller, "unknown"

        if not controller.get_devices():
            return controller, "no_devices"
        return controller, None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle username / password entry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            controller, error = await self._async_validate(
                user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
            )
            try:
                if error:
                    errors["base"] = error
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
            finally:
                await controller.stop()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle re-authentication when stored credentials stop working."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm re-authentication with a new password."""
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()
        username = reauth_entry.data[CONF_USERNAME]

        if user_input is not None:
            controller, error = await self._async_validate(
                username, user_input[CONF_PASSWORD]
            )
            try:
                if error:
                    errors["base"] = error
                else:
                    return self.async_update_reload_and_abort(
                        reauth_entry,
                        data_updates={CONF_PASSWORD: user_input[CONF_PASSWORD]},
                    )
            finally:
                await controller.stop()

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            errors=errors,
            description_placeholders={CONF_USERNAME: username},
        )
