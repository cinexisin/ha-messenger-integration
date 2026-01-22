import json
import logging
import homeassistant.helpers.config_validation as cv
import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import HomeAssistantError

from .const import (
    DOMAIN,
    CONF_ADDON_SLUG,
    CONF_NOTIFY_SERVICE,
    CONF_DEFAULT_CHANNEL,
)

_LOGGER = logging.getLogger(__name__)


def _channels_to_list(value: str):
    s = (value or "").strip().lower()
    if s == "both":
        return ["telegram", "whatsapp"]
    if s == "telegram":
        return ["telegram"]
    return ["whatsapp"]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    addon_slug = (entry.data.get(CONF_ADDON_SLUG) or "").strip()
    notify_name = (entry.data.get(CONF_NOTIFY_SERVICE) or "cinexis").strip().lower()
    default_channel = entry.data.get(CONF_DEFAULT_CHANNEL) or "whatsapp"

    if not addon_slug:
        raise HomeAssistantError("Cinexis Messenger: addon_slug is empty. Configure the integration.")

    async def _send_to_addon(payload: dict):
        # Supervisor service that writes to add-on STDIN
        if not hass.services.has_service("hassio", "addon_stdin"):
            raise HomeAssistantError("Supervisor service hassio.addon_stdin not available")
        await hass.services.async_call(
            "hassio",
            "addon_stdin",
            {"addon": addon_slug, "input": json.dumps(payload, ensure_ascii=False)},
            blocking=False,
        )

    # ---------- Notify-style services (so you can use the Notifications action card) ----------
    notify_schema = vol.Schema(
        {
            vol.Required("message"): vol.Any(str, object),
            vol.Optional("title"): vol.Any(str, object),
            vol.Optional("target"): vol.Any(str, [str], object),
            vol.Optional("data"): dict,
        },
        extra=vol.ALLOW_EXTRA,
    )

    async def _handle_notify(call: ServiceCall, channels_override=None):
        message = str(call.data.get("message", "") or "")
        title = call.data.get("title")
        target = call.data.get("target")
        data = call.data.get("data") or {}

        channels = channels_override or _channels_to_list(default_channel)

        payload = {
            "message": message,
            "title": title,
            "target": target,   # can be one line, multiline, list; add-on normalizes
            "data": data,       # can contain camera_entity_id
            "channels": channels
        }
        await _send_to_addon(payload)

    def _try_register_notify(service: str, channels_override):
        if hass.services.has_service("notify", service):
            _LOGGER.warning("notify.%s already exists; skipping registration", service)
            return
        hass.services.async_register(
            "notify",
            service,
            lambda call: _handle_notify(call, channels_override),
            schema=notify_schema,
        )

    _try_register_notify(notify_name, None)
    _try_register_notify(f"{notify_name}_whatsapp", ["whatsapp"])
    _try_register_notify(f"{notify_name}_telegram", ["telegram"])
    _try_register_notify(f"{notify_name}_both", ["telegram", "whatsapp"])

    # ---------- Automation-friendly services with nice UI selectors ----------
    send_schema = vol.Schema(
        {
            vol.Optional("channels", default=default_channel): vol.In(["whatsapp", "telegram", "both"]),
            vol.Optional("targets"): vol.Any(str, [str]),
            vol.Optional("title"): cv.string,
            vol.Required("message"): cv.string,
            vol.Optional("camera_entity_id"): cv.entity_id,
        },
        extra=vol.ALLOW_EXTRA,
    )

    async def handle_send(call: ServiceCall):
        channels = _channels_to_list(call.data.get("channels", default_channel))
        targets = call.data.get("targets")
        title = call.data.get("title")
        message = call.data.get("message")
        camera_entity_id = call.data.get("camera_entity_id")

        data = {}
        if camera_entity_id:
            data["camera_entity_id"] = camera_entity_id

        payload = {
            "channels": channels,
            "title": title,
            "message": message,
            "target": targets,
            "data": data
        }
        await _send_to_addon(payload)

    report_schema = vol.Schema(
        {
            vol.Optional("channels", default=default_channel): vol.In(["whatsapp", "telegram", "both"]),
            vol.Optional("targets"): vol.Any(str, [str]),
            vol.Optional("title", default="Devices left ON"): cv.string,
            vol.Required("entities"): vol.All(cv.ensure_list, [cv.entity_id]),
            vol.Optional("send_when_none_on", default=False): cv.boolean,
        },
        extra=vol.ALLOW_EXTRA,
    )

    async def handle_report(call: ServiceCall):
        channels = _channels_to_list(call.data.get("channels", default_channel))
        targets = call.data.get("targets")
        title = call.data.get("title") or "Devices left ON"
        entities = call.data.get("entities") or []
        send_when_none_on = bool(call.data.get("send_when_none_on", False))

        on_list = []
        for ent in entities:
            st = hass.states.get(ent)
            name = (st.name if st else ent)
            state = (st.state if st else "unknown")
            if state == "on":
                on_list.append(name)

        if not on_list and not send_when_none_on:
            _LOGGER.info("Cinexis report: nothing ON, not sending.")
            return

        if on_list:
            msg = "ON ({}):\n{}".format(len(on_list), "\n".join([f"- {n}" for n in on_list]))
        else:
            msg = "No selected devices are ON."

        payload = {
            "channels": channels,
            "title": title,
            "message": msg,
            "target": targets,
            "data": {}
        }
        await _send_to_addon(payload)

    hass.services.async_register(DOMAIN, "send", handle_send, schema=send_schema)
    hass.services.async_register(DOMAIN, "report_on_entities", handle_report, schema=report_schema)

    return True
