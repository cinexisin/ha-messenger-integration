import re
import voluptuous as vol

from homeassistant import config_entries
from .const import (
    DOMAIN,
    CONF_ADDON_SLUG,
    CONF_NOTIFY_SERVICE,
    CONF_DEFAULT_CHANNEL,
    DEFAULT_NOTIFY_SERVICE,
    DEFAULT_CHANNEL,
)

SERVICE_RE = re.compile(r"^[a-z0-9_]+$")


class CinexisConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        errors = {}

        if user_input is not None:
            notify_service = (user_input.get(CONF_NOTIFY_SERVICE) or "").strip().lower()
            addon_slug = (user_input.get(CONF_ADDON_SLUG) or "").strip()

            if not addon_slug:
                errors[CONF_ADDON_SLUG] = "required"

            if not SERVICE_RE.match(notify_service):
                errors[CONF_NOTIFY_SERVICE] = "invalid_service_name"

            if not errors:
                return self.async_create_entry(title="Cinexis Messenger", data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_NOTIFY_SERVICE, default=DEFAULT_NOTIFY_SERVICE): str,
                vol.Required(CONF_ADDON_SLUG, default=""): str,
                vol.Required(CONF_DEFAULT_CHANNEL, default=DEFAULT_CHANNEL): vol.In(
                    ["whatsapp", "telegram", "both"]
                ),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
