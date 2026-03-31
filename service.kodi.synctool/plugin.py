import sys
from urllib.parse import parse_qsl

from resources.lib.kodi_compat import (
    browse_path,
    get_addon,
    get_setting_string,
    log,
    set_setting_string,
    show_ok_dialog,
    translate_path,
)
from resources.lib.pairing_flow import pairing_entrypoint
from resources.lib.sync_engine import manual_sync_entrypoint


def _query_params():
    raw_query = ""
    if len(sys.argv) > 2:
        raw_query = (sys.argv[2] or "").lstrip("?")
    return dict(parse_qsl(raw_query))


def _slot_number(params):
    slot = params.get("slot", "")
    return slot if slot in ("1", "2", "3") else ""


def _addon_backup_relative_path(selected_path):
    addon_data_special = "special://profile/addon_data/"
    addon_data_path = translate_path(addon_data_special).rstrip("/\\")
    raw_selected = (selected_path or "").rstrip("/\\")
    if not raw_selected:
        return ""
    if raw_selected.startswith(addon_data_path + "/") or raw_selected.startswith(addon_data_path + "\\"):
        return raw_selected[len(addon_data_path) + 1 :].replace("\\", "/")
    if raw_selected.startswith(addon_data_special):
        return raw_selected[len(addon_data_special) :].replace("\\", "/")
    return ""


def _browse_addon_backup(addon, slot):
    selected_path = browse_path(
        "directory",
        "Select add-on settings folder",
        translate_path("special://profile/addon_data/"),
    )
    if not selected_path:
        return
    relative_path = _addon_backup_relative_path(selected_path)
    if not relative_path:
        show_ok_dialog(
            "Kodi Sync Tool",
            "Choose a folder inside special://profile/addon_data/.",
        )
        return
    set_setting_string(addon, "addon_backup_%s_path" % slot, relative_path)


def _browse_custom_path(addon, slot):
    kind_value = get_setting_string(addon, "custom_%s_kind" % slot, "file")
    browse_kind = "directory" if kind_value == "directory" else "file"
    current_value = get_setting_string(addon, "custom_%s_path" % slot, "")
    default_path = translate_path(current_value) if current_value else translate_path("special://profile/")
    selected_path = browse_path(browse_kind, "Select custom sync %s" % browse_kind, default_path)
    if not selected_path:
        return
    set_setting_string(addon, "custom_%s_path" % slot, selected_path)


def run():
    addon = get_addon()
    params = _query_params()
    action = params.get("action", "")
    log("Plugin route invoked: %s" % (action or "<none>"), addon=addon)

    if action == "pair_google_drive":
        set_setting_string(addon, "pair_on_next_startup", "false")
        pairing_entrypoint()
        return
    if action == "sync_now":
        manual_sync_entrypoint()
        return
    if action == "browse_addon_backup":
        slot = _slot_number(params)
        if slot:
            _browse_addon_backup(addon, slot)
        else:
            log("Browse addon backup requested without valid slot", level="warning", addon=addon)
        return
    if action == "browse_custom_path":
        slot = _slot_number(params)
        if slot:
            _browse_custom_path(addon, slot)
        else:
            log("Browse custom path requested without valid slot", level="warning", addon=addon)
        return

    log("Unknown plugin action: %s" % (action or "<none>"), level="warning", addon=addon)


if __name__ == "__main__":
    run()
