# KodiSkin Widget Importer

Kodi script add-on for importing Skin Shortcuts widget backups from a ZIP file, direct URL, network path, local path, or pCloud public link.

## What it imports

- `skin.*-*.DATA.xml` files from `userdata/addon_data/script.skinshortcuts`
- `skin.*.properties`
- optional `script-skinshortcuts-includes.xml` if the ZIP contains it and you confirm the extra copy

The add-on renames the source skin prefix to the currently active Kodi skin. For example:

```text
skin.arctic.horizon.2.patched-tvshows-1.DATA.xml
```

becomes:

```text
<current-active-skin>-tvshows-1.DATA.xml
```

It does not import the source `.hash` file. Instead it backs up and removes the local hash for the active skin so Skin Shortcuts rebuilds the generated include after you reload the skin or restart Kodi.

## Usage

1. Install the ZIP package for this add-on in Kodi.
2. Run **KodiSkin Widget Importer** from Program add-ons.
3. Paste a pCloud public link, direct ZIP URL, local ZIP path, or network ZIP path, or browse for a local ZIP.
4. Confirm the source skin and target skin shown by the add-on.
5. Reload the skin or restart Kodi.

Backups of overwritten files are stored under:

```text
special://profile/addon_data/script.kodiskin.widget.importer/backups/
```
