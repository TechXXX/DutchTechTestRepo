import hashlib
import os
import traceback
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, unquote

from resources.lib.drive_api import APPDATA_SCOPE, DRIVE_FILE_SCOPE, DriveClient, DriveError, OAuthTokenProvider
from resources.lib.kodi_compat import (
    get_addon,
    get_monitor,
    get_setting_bool,
    get_setting_string,
    log,
    notify,
    now_iso,
    profile_dir,
    set_setting_string,
    translate_path,
)
from resources.lib.state import load_state, save_state


REMOTE_PREFIX = "kodi-sync-tool--"
FILE_TOKEN = "file"


def _mtime_to_datetime(timestamp):
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def _file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_file_bytes(path):
    with open(path, "rb") as handle:
        return handle.read()


def _write_file_bytes(path, content):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(content)


def _local_metadata(path):
    if not os.path.exists(path):
        return None
    stat_result = os.stat(path)
    return {
        "path": path,
        "modified_time": _mtime_to_datetime(stat_result.st_mtime),
        "size": stat_result.st_size,
        "sha256": _file_sha256(path),
    }


def _directory_file_map(path):
    files = {}
    if not os.path.isdir(path):
        return files
    for root, _dirs, filenames in os.walk(path):
        for filename in filenames:
            full_path = os.path.join(root, filename)
            relative_path = os.path.relpath(full_path, path).replace(os.sep, "/")
            files[relative_path] = _local_metadata(full_path)
    return files


def decide_sync_direction(local_meta, remote_meta, upload_local_changes):
    if local_meta and remote_meta:
        local_time = local_meta["modified_time"]
        remote_time = remote_meta["modified_time"]

        if local_meta.get("sha256") == remote_meta.get("sha256"):
            return "noop"
        if remote_time and local_time and remote_time > local_time:
            return "download"
        if local_time and remote_time and local_time > remote_time:
            return "upload" if upload_local_changes else "noop"
        if remote_time and not local_time:
            return "download"
        if local_time and not remote_time:
            return "upload" if upload_local_changes else "noop"
        return "noop"

    if remote_meta and not local_meta:
        return "download"
    if local_meta and not remote_meta:
        return "upload" if upload_local_changes else "noop"
    return "noop"


def _sync_result(status, direction, message, local_meta=None, remote_meta=None, target_id="", target_label=""):
    return {
        "status": status,
        "direction": direction,
        "message": message,
        "target_id": target_id,
        "target_label": target_label,
        "local_modified_time": to_iso(local_meta["modified_time"]) if local_meta and local_meta.get("modified_time") else None,
        "remote_modified_time": to_iso(remote_meta["modified_time"]) if remote_meta and remote_meta.get("modified_time") else None,
        "completed_at": now_iso(),
    }


def to_iso(value):
    if value is None:
        return None
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def selected_scopes(remote_mode):
    scopes = [APPDATA_SCOPE]
    if remote_mode in ("drive_file", "file_id"):
        scopes.append(DRIVE_FILE_SCOPE)
    return scopes


def _scope_contains(granted_scope, expected_scope):
    if not granted_scope or not expected_scope:
        return False
    return expected_scope in granted_scope.split()


def parse_expiry(raw_value):
    if not raw_value:
        return None
    try:
        return datetime.fromisoformat(raw_value)
    except ValueError:
        return None


def build_drive_client(addon):
    remote_mode = get_setting_string(addon, "remote_mode", "appdata") or "appdata"
    client = OAuthTokenProvider(
        client_id="",
        client_secret="",
        refresh_token=get_setting_string(addon, "oauth_refresh_token", ""),
        refresh_secret=get_setting_string(addon, "oauth_refresh_secret", ""),
        scopes=selected_scopes(remote_mode),
        access_token=get_setting_string(addon, "oauth_access_token", ""),
        access_token_expiry=parse_expiry(get_setting_string(addon, "oauth_access_token_expires_at", "")),
        refresh_bridge_url=get_setting_string(addon, "oauth_bridge_url", ""),
    )
    return DriveClient(client), remote_mode


def persist_oauth_tokens(addon, token_payload):
    refresh_token = token_payload.get("refresh_token")
    refresh_secret = token_payload.get("refresh_secret")
    access_token = token_payload.get("access_token")
    expires_in = token_payload.get("expires_in")
    granted_scope = token_payload.get("scope")
    log(
        "Persisting OAuth tokens: refresh_token_present=%s refresh_secret_present=%s access_token_present=%s expires_in=%s scope_present=%s"
        % (
            bool(refresh_token),
            bool(refresh_secret),
            bool(access_token),
            expires_in if expires_in is not None else "",
            bool(granted_scope),
        ),
        addon=addon,
    )

    if refresh_token:
        set_setting_string(addon, "oauth_refresh_token", refresh_token)
        stored_refresh_token = get_setting_string(addon, "oauth_refresh_token", "")
        log(
            "Stored oauth_refresh_token: persisted=%s length=%s"
            % (bool(stored_refresh_token), len(stored_refresh_token)),
            addon=addon,
        )
    if refresh_secret:
        set_setting_string(addon, "oauth_refresh_secret", refresh_secret)
        stored_refresh_secret = get_setting_string(addon, "oauth_refresh_secret", "")
        log(
            "Stored oauth_refresh_secret: persisted=%s length=%s"
            % (bool(stored_refresh_secret), len(stored_refresh_secret)),
            addon=addon,
        )
    if access_token:
        set_setting_string(addon, "oauth_access_token", access_token)
        stored_access_token = get_setting_string(addon, "oauth_access_token", "")
        log(
            "Stored oauth_access_token: persisted=%s length=%s"
            % (bool(stored_access_token), len(stored_access_token)),
            addon=addon,
        )
    if expires_in:
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
        set_setting_string(addon, "oauth_access_token_expires_at", expires_at.isoformat())
        stored_expiry = get_setting_string(addon, "oauth_access_token_expires_at", "")
        log(
            "Stored oauth_access_token_expires_at: persisted=%s value=%s"
            % (bool(stored_expiry), stored_expiry),
            addon=addon,
        )
    if granted_scope:
        set_setting_string(addon, "oauth_scope", granted_scope)
        stored_scope = get_setting_string(addon, "oauth_scope", "")
        log(
            "Stored oauth_scope: persisted=%s length=%s"
            % (bool(stored_scope), len(stored_scope)),
            addon=addon,
        )


def _file_target(target_id, label, local_path, setting_id):
    return {
        "id": target_id,
        "label": label,
        "kind": "file",
        "setting_id": setting_id,
        "local_path": translate_path(local_path),
    }


def _directory_target(target_id, label, local_path, setting_id):
    return {
        "id": target_id,
        "label": label,
        "kind": "directory",
        "setting_id": setting_id,
        "local_path": translate_path(local_path),
    }


def _custom_slot_kind(addon, slot):
    raw = get_setting_string(addon, "custom_%s_kind" % slot, "file")
    return "directory" if raw in ("1", "directory") else "file"


def build_targets(addon):
    targets = [
        _file_target("favourites", "Favourites", "special://profile/favourites.xml", "sync_favourites"),
        _file_target("sources", "Sources", "special://profile/sources.xml", "sync_sources"),
        _file_target("passwords", "Passwords", "special://profile/passwords.xml", "sync_passwords"),
        _file_target("guisettings", "GUI Settings", "special://profile/guisettings.xml", "sync_guisettings"),
        _directory_target("keymaps", "Keymaps", "special://profile/keymaps/", "sync_keymaps"),
        _directory_target(
            "skin_widgets",
            "Skin Widgets",
            "special://profile/addon_data/script.skinshortcuts/",
            "sync_skin_widgets",
        ),
    ]

    for slot in ("1", "2", "3"):
        relative_path = get_setting_string(addon, "addon_backup_%s_path" % slot, "").strip().strip("/\\")
        targets.append(
            {
                "id": "addon_backup_%s" % slot,
                "label": "Addon Settings Backup %s" % slot,
                "kind": "directory",
                "setting_id": "addon_backup_%s_enabled" % slot,
                "local_path": translate_path("special://profile/addon_data/%s" % relative_path) if relative_path else "",
                "configured_value": relative_path,
            }
        )

    for slot in ("1", "2", "3"):
        custom_path = get_setting_string(addon, "custom_%s_path" % slot, "").strip()
        targets.append(
            {
                "id": "custom_%s" % slot,
                "label": "Custom %s" % slot,
                "kind": _custom_slot_kind(addon, slot),
                "setting_id": "custom_%s_enabled" % slot,
                "local_path": translate_path(custom_path) if custom_path else "",
                "configured_value": custom_path,
            }
        )

    return targets


def enabled_targets(addon):
    return [target for target in build_targets(addon) if get_setting_bool(addon, target["setting_id"], False)]


def _target_prefix(target):
    return "%s%s--" % (REMOTE_PREFIX, target["id"])


def _encode_relative_path(value):
    return quote((value or FILE_TOKEN).replace("\\", "/"), safe="")


def _decode_relative_path(value):
    decoded = unquote(value or FILE_TOKEN)
    return "" if decoded == FILE_TOKEN else decoded


def _target_remote_name(target, relative_path=""):
    return _target_prefix(target) + _encode_relative_path(relative_path)


def _remote_relative_path(target, name):
    prefix = _target_prefix(target)
    if not name.startswith(prefix):
        return None
    return _decode_relative_path(name[len(prefix) :])


def _target_is_configured(target):
    if target["kind"] == "file":
        return bool(target["local_path"])
    return bool(target["local_path"])


def _skip_target_result(target, message):
    return _sync_result("ok", "noop", message, target_id=target["id"], target_label=target["label"])


def _list_remote_directory_files(client, target, drive_folder_id, remote_mode):
    if remote_mode == "file_id":
        return {}
    remote_entries = client.list_files(folder_id=drive_folder_id, remote_mode=remote_mode, name_prefix=_target_prefix(target))
    remote_map = {}
    for item in remote_entries:
        relative_path = _remote_relative_path(target, item.get("name") or "")
        if relative_path is None:
            continue
        remote_map[relative_path] = item
    return remote_map


def _sync_file_target(client, addon, target, drive_file_id, drive_folder_id, remote_mode, upload_local_changes):
    local_path = target["local_path"]
    remote_meta = None
    remote_name = _target_remote_name(target)
    if remote_mode == "file_id":
        if target["id"] != "favourites":
            return _skip_target_result(target, "%s skipped because remote_mode=file_id only supports Favourites." % target["label"])
        remote_meta = client.resolve_remote(drive_file_id, drive_folder_id, get_setting_string(addon, "remote_filename", "favourites.xml"), remote_mode=remote_mode)
    else:
        remote_meta = client.resolve_remote("", drive_folder_id, remote_name, remote_mode=remote_mode)

    local_meta = _local_metadata(local_path)
    remote_bytes = None

    if remote_meta and local_meta:
        remote_bytes = client.download_file(remote_meta["id"])
        remote_meta["sha256"] = hashlib.sha256(remote_bytes).hexdigest()
    elif remote_meta:
        remote_meta["sha256"] = None

    direction = decide_sync_direction(local_meta, remote_meta, upload_local_changes)
    log("Sync decision for %s: %s" % (target["label"], direction), verbose_only=True, addon=addon)

    if direction == "download":
        if not remote_meta:
            raise DriveError("Remote file metadata is missing for %s download" % target["label"])
        content = remote_bytes if remote_bytes is not None else client.download_file(remote_meta["id"])
        _write_file_bytes(local_path, content)
        if remote_meta["modified_time"] is not None:
            timestamp = remote_meta["modified_time"].timestamp()
            os.utime(local_path, (timestamp, timestamp))
        local_meta = _local_metadata(local_path)
        return _sync_result(
            "ok",
            "download",
            "Downloaded newer remote %s" % target["label"],
            local_meta,
            remote_meta,
            target["id"],
            target["label"],
        )

    if direction == "upload":
        if not local_meta:
            return _skip_target_result(target, "%s is missing locally, nothing to upload." % target["label"])
        content = _read_file_bytes(local_path)
        if remote_meta:
            upload_name = remote_meta.get("name") or remote_name
            remote_meta = client.update_file(remote_meta["id"], upload_name, content)
        else:
            upload_name = get_setting_string(addon, "remote_filename", "favourites.xml") if remote_mode == "file_id" else remote_name
            remote_meta = client.create_file(drive_folder_id, upload_name, content, remote_mode=remote_mode)
        return _sync_result(
            "ok",
            "upload",
            "Uploaded newer local %s" % target["label"],
            local_meta,
            remote_meta,
            target["id"],
            target["label"],
        )

    return _sync_result(
        "ok",
        "noop",
        "%s is already in sync" % target["label"],
        local_meta,
        remote_meta,
        target["id"],
        target["label"],
    )


def _sync_directory_target(client, addon, target, drive_folder_id, remote_mode, upload_local_changes):
    if remote_mode == "file_id":
        return _skip_target_result(target, "%s skipped because remote_mode=file_id does not support directory targets." % target["label"])

    local_root = target["local_path"]
    remote_map = _list_remote_directory_files(client, target, drive_folder_id, remote_mode)
    local_map = _directory_file_map(local_root)
    relative_paths = sorted(set(local_map.keys()) | set(remote_map.keys()))

    if not relative_paths and not os.path.isdir(local_root):
        return _skip_target_result(target, "%s is not present locally and has no remote backup yet." % target["label"])

    downloaded = 0
    uploaded = 0
    unchanged = 0

    for relative_path in relative_paths:
        local_meta = local_map.get(relative_path)
        remote_meta = remote_map.get(relative_path)
        remote_bytes = None
        if remote_meta and local_meta:
            remote_bytes = client.download_file(remote_meta["id"])
            remote_meta["sha256"] = hashlib.sha256(remote_bytes).hexdigest()
        elif remote_meta:
            remote_meta["sha256"] = None

        direction = decide_sync_direction(local_meta, remote_meta, upload_local_changes)
        file_path = os.path.join(local_root, relative_path.replace("/", os.sep))
        log(
            "Sync decision for %s [%s]: %s" % (target["label"], relative_path or FILE_TOKEN, direction),
            verbose_only=True,
            addon=addon,
        )

        if direction == "download":
            content = remote_bytes if remote_bytes is not None else client.download_file(remote_meta["id"])
            _write_file_bytes(file_path, content)
            if remote_meta["modified_time"] is not None:
                timestamp = remote_meta["modified_time"].timestamp()
                os.utime(file_path, (timestamp, timestamp))
            downloaded += 1
            continue

        if direction == "upload":
            if not local_meta:
                continue
            content = _read_file_bytes(file_path)
            remote_name = _target_remote_name(target, relative_path)
            if remote_meta:
                remote_name = remote_meta.get("name") or remote_name
                client.update_file(remote_meta["id"], remote_name, content)
            else:
                client.create_file(drive_folder_id, remote_name, content, remote_mode=remote_mode)
            uploaded += 1
            continue

        unchanged += 1

    if downloaded:
        message = "Downloaded %s file(s) for %s" % (downloaded, target["label"])
        direction = "download" if not uploaded else "mixed"
    elif uploaded:
        message = "Uploaded %s file(s) for %s" % (uploaded, target["label"])
        direction = "upload"
    else:
        message = "%s is already in sync" % target["label"]
        direction = "noop"
    if downloaded and uploaded:
        message = "Synced %s: %s downloaded, %s uploaded, %s unchanged" % (
            target["label"],
            downloaded,
            uploaded,
            unchanged,
        )
    return _sync_result("ok", direction, message, target_id=target["id"], target_label=target["label"])


def _sync_single_target(client, addon, target, drive_file_id, drive_folder_id, remote_mode, upload_local_changes):
    if not _target_is_configured(target):
        configured_value = target.get("configured_value", "")
        if target["id"].startswith("addon_backup_"):
            return _skip_target_result(target, "%s is enabled but no addon settings folder is selected." % target["label"])
        if target["id"].startswith("custom_"):
            return _skip_target_result(target, "%s is enabled but no path is configured." % target["label"])
        return _skip_target_result(target, "%s is not configured." % target["label"])

    try:
        if target["kind"] == "directory":
            return _sync_directory_target(client, addon, target, drive_folder_id, remote_mode, upload_local_changes)
        return _sync_file_target(client, addon, target, drive_file_id, drive_folder_id, remote_mode, upload_local_changes)
    except Exception as exc:  # pylint: disable=broad-except
        log("Sync failed for %s: %s" % (target["label"], exc), level="error", addon=addon)
        log("Target sync traceback:\n%s" % traceback.format_exc(), level="error", addon=addon)
        return _sync_result("error", "noop", "%s failed: %s" % (target["label"], exc), target_id=target["id"], target_label=target["label"])


def _overall_direction(target_results):
    directions = {item["direction"] for item in target_results if item.get("direction") not in ("", None, "noop")}
    if not directions:
        return "noop"
    if len(directions) == 1:
        return list(directions)[0]
    return "mixed"


def _build_summary_message(target_results):
    errors = [item for item in target_results if item["status"] == "error"]
    downloads = [item for item in target_results if item["direction"] == "download"]
    uploads = [item for item in target_results if item["direction"] == "upload"]
    mixed = [item for item in target_results if item["direction"] == "mixed"]
    active = len(target_results)
    if errors:
        return "Synced %s targets with %s error(s)." % (active, len(errors))
    if downloads or uploads or mixed:
        return "Synced %s targets: %s download, %s upload, %s mixed." % (
            active,
            len(downloads),
            len(uploads),
            len(mixed),
        )
    return "All %s enabled sync targets are already in sync." % active


def perform_sync(addon=None, reason="manual"):
    addon = addon or get_addon()
    addon_profile = profile_dir(addon)
    state = load_state(addon_profile)

    log("Starting sync (%s)" % reason, addon=addon)
    drive_file_id = get_setting_string(addon, "drive_file_id", "")
    drive_folder_id = get_setting_string(addon, "drive_folder_id", "")
    upload_local_changes = get_setting_bool(addon, "upload_local_changes", True)
    oauth_refresh_token = get_setting_string(addon, "oauth_refresh_token", "")
    oauth_access_token = get_setting_string(addon, "oauth_access_token", "")
    oauth_scope = get_setting_string(addon, "oauth_scope", "")
    oauth_bridge_url = get_setting_string(addon, "oauth_bridge_url", "")
    targets = enabled_targets(addon)
    log("Setting check: upload_local_changes=%s enabled_targets=%s" % (upload_local_changes, len(targets)), addon=addon)

    if not targets:
        result = _sync_result("ok", "noop", "No sync targets are enabled.")
        persist_results(addon_profile, state, result, [])
        return result

    if not oauth_refresh_token and not oauth_access_token:
        if oauth_bridge_url:
            result = _sync_result(
                "ok",
                "noop",
                "Google Drive is not paired yet. Run the pairing action before startup sync can use OAuth.",
            )
            persist_results(addon_profile, state, result, [])
            return result
        result = _sync_result(
            "error",
            "noop",
            "OAuth bridge URL is not configured and no OAuth token is available",
        )
        persist_results(addon_profile, state, result, [])
        return result

    client, remote_mode = build_drive_client(addon)
    log(
        "OAuth scope check: remote_mode=%s appdata_granted=%s drive_file_granted=%s scope=%s"
        % (
            remote_mode,
            _scope_contains(oauth_scope, APPDATA_SCOPE),
            _scope_contains(oauth_scope, DRIVE_FILE_SCOPE),
            oauth_scope or "",
        ),
        addon=addon,
    )

    target_results = [_sync_single_target(client, addon, target, drive_file_id, drive_folder_id, remote_mode, upload_local_changes) for target in targets]
    overall_status = "error" if any(item["status"] == "error" for item in target_results) else "ok"
    result = {
        "status": overall_status,
        "direction": _overall_direction(target_results),
        "message": _build_summary_message(target_results),
        "completed_at": now_iso(),
        "targets": target_results,
    }
    persist_results(addon_profile, state, result, target_results)
    return result


def persist_results(addon_profile, state, result, target_results):
    new_state = dict(state)
    new_state["last_sync"] = result["completed_at"]
    new_state["last_direction"] = result["direction"]
    new_state["last_status"] = result["status"]
    new_state["last_error"] = result["message"] if result["status"] == "error" else ""
    new_state["targets"] = {}
    for item in target_results:
        new_state["targets"][item["target_id"]] = {
            "status": item["status"],
            "direction": item["direction"],
            "message": item["message"],
            "local_modified_time": item.get("local_modified_time"),
            "remote_modified_time": item.get("remote_modified_time"),
            "completed_at": item["completed_at"],
        }
    save_state(addon_profile, new_state)


def service_main():
    addon = get_addon()
    monitor = get_monitor()
    if get_setting_bool(addon, "pair_on_next_startup", False):
        log("Launching Google Drive pairing from startup fallback toggle", addon=addon)
        set_setting_string(addon, "pair_on_next_startup", "false")
        from resources.lib.pairing_flow import pair_google_drive

        pair_google_drive(addon=addon)
    if get_setting_bool(addon, "sync_on_startup", True):
        result = perform_sync(addon=addon, reason="startup")
        _notify_if_needed(addon, result, manual=False)
    else:
        log("Startup sync is disabled", addon=addon)

    while not monitor.abortRequested():
        if monitor.waitForAbort(30):
            break


def manual_sync_entrypoint():
    addon = get_addon()
    result = perform_sync(addon=addon, reason="manual")
    _notify_if_needed(addon, result, manual=True)


def _notify_if_needed(addon, result, manual):
    direction = result["direction"]
    message = result["message"]
    log("%s: %s" % (direction, message), addon=addon)
    if manual or result["status"] == "error":
        heading = "Kodi Sync Tool"
        notify(addon, heading, message)
