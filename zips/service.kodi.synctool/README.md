# Kodi Sync Tool

Kodi service add-on that syncs selected Kodi data across devices using Google
Drive and a browser-based OAuth pairing flow.

This README is written for maintainers and future agents first, while still
keeping the main user setup and security notes in one place.

## What Makes This Addon Different

Compared with the older single-file favourites sync add-on, this add-on can
sync multiple target categories:

- core Kodi data such as favourites, sources, passwords, GUI settings, and
  keymaps
- skin widget data
- up to 3 add-on settings folders under `addon_data`
- up to 3 custom file or folder targets

The shipping model stays intentionally simple in Kodi:

- pair once with Google Drive
- sync automatically on Kodi startup
- optionally run `Sync now`
- keep remote storage in Google Drive app data

## Maintainer File Map

- `addon.xml`
  Kodi metadata and entrypoints.
- `plugin.py`
  Settings-driven `RunPlugin(...)` routes. Handles pairing, manual sync, and
  the browse actions for add-on-backup and custom-path slots.
- `pair_google_drive.py`
  Direct entrypoint that launches the pairing flow.
- `sync_now.py`
  Direct entrypoint for a manual sync run.
- `service.py`
  Startup service entrypoint. This is what Kodi calls on boot.
- `resources/settings.xml`
  User-facing settings, grouped into the visible categories shown in Kodi.
- `resources/lib/pairing_flow.py`
  Coordinates pairing creation, dialog display, browser/QR flow, polling, and
  token claim.
- `resources/lib/pairing_dialog.py`
  Pairing UI dialog and QR presentation.
- `resources/lib/oauth_bridge.py`
  Client for the external auth bridge.
- `resources/lib/drive_api.py`
  Google Drive HTTP calls and remote storage operations.
- `resources/lib/sync_engine.py`
  Enumerates enabled targets, compares timestamps, and decides upload vs
  download.
- `resources/lib/state.py`
  Persists OAuth and sync state in Kodi settings.
- `resources/lib/kodi_compat.py`
  Kodi-version-safe wrappers for logging, dialogs, settings, and filesystem
  access.
- `CHANGELOG.md`
  Release history only. Read this README for the current shipped behavior.

## Runtime Flow

There are three main ways this addon runs:

1. Kodi startup
   `service.py` calls `service_main()` in `sync_engine.py`, which checks
   pairing state and sync settings, then performs the enabled sync work.
2. Pairing
   `plugin.py?action=pair_google_drive` or `pair_google_drive.py` enters the
   browser pairing flow.
3. Manual sync
   `plugin.py?action=sync_now` or `sync_now.py` runs the sync engine on demand.

The extra browse actions are specific to this multi-target add-on:

- `browse_addon_backup`
- `browse_custom_path`

Those routes validate selected paths before storing them in settings.

## User Setup

1. Install the add-on.
2. Open add-on settings.
3. Select `Pair Google Drive now`.
4. Complete the sign-in flow in your browser or on your phone.
5. Leave `Sync on Kodi startup` enabled.

After pairing, the add-on syncs the enabled targets each time Kodi starts.

## How Sync Decides What To Do

- Remote storage uses Google Drive app data by default.
- The backup is not intended to appear in the normal Drive file list.
- Sync behavior is last-write-wins per target.
- Each target is evaluated independently.

That means the newest version of each individual target seen during a sync run
becomes the winning version for that target.

## Visible Settings Groups

- `Pair Google Drive now`
- `Sync now`
- `Sync on Kodi startup`
- `Core Data`
- `Skin`
- `Addon Settings Backup`
- `Custom`

The add-on also keeps internal OAuth and storage settings for compatibility, so
not every stored value is meant for direct user editing.

## OAuth Bridge

Browser sign-in is handled through the Vercel auth bridge.

Current bridge URL:

- `https://auth-bridge-rho.vercel.app`

## Security Model

The add-on does not contain a Google client secret.

Google sign-in happens in a browser through the auth bridge. Kodi shows a
pairing code, the user completes Google sign-in in the browser, and the bridge
returns tokens through a short-lived pairing record.

Important security properties:

- no Google client secret inside Kodi
- no manual token copy-paste flow
- one-time token handoff from the bridge to Kodi
- short-lived pairing sessions with explicit expiry
- no public token refresh endpoint

Kodi stores OAuth state in settings after pairing:

- `oauth_refresh_token`
- `oauth_refresh_secret`
- `oauth_access_token`
- `oauth_scope`
- token expiry metadata

The additional `oauth_refresh_secret` is required before the bridge will
exchange a stored refresh token for a new access token.

## Pairing Flow

1. In Kodi, run `Pair Google Drive now`.
2. The add-on asks the bridge for a pairing session.
3. Kodi shows a code and activation URL.
4. The user signs into Google in a browser.
5. Google redirects back to the bridge.
6. The bridge marks the pairing as authorized.
7. Kodi claims the token payload and stores it locally.

## Future-Agent Guard Rails

- Keep browser OAuth on the bridge side. Do not move the Google client secret
  into Kodi.
- Preserve the `plugin.py` browse-slot validation for add-on-backup and custom
  paths.
- If startup sync breaks, inspect `sync_engine.py` and Kodi settings/state
  handling before changing the pairing flow.
- If pairing breaks, inspect bridge communication first, not just the local
  dialog code.
