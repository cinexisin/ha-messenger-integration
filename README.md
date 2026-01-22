# Cinexis Messenger (Integration)

This integration adds clean Automation UI actions/services to send messages through the **HA Messenger add-on**.

## Install (GitHub-only)
1) Install the HA add-on repository:
   - Settings → Add-ons → Add-on store → ⋮ → Repositories
   - Add: https://github.com/cinexisin/ha-messenger

2) Install this integration via HACS:
   - HACS → Integrations → ⋮ → Custom repositories
   - Add this repo URL and choose type **Integration**
   - Install and restart Home Assistant

3) Add integration:
   - Settings → Devices & services → Add integration → "Cinexis Messenger"
   - Enter your add-on slug (e.g. `2d122300_ha_messenger`)
   - Pick default channel (whatsapp/telegram/both)

## Services (used in Automations UI)
- `cinexis.send` → title + message + one/multiple targets (+countrycode) + optional camera snapshot
- `cinexis.report_on_entities` → at a scheduled time, send only ON devices list

## Optional notify-style actions
This integration also registers notify services:
- `notify.cinexis`
- `notify.cinexis_whatsapp`
- `notify.cinexis_telegram`
- `notify.cinexis_both`
