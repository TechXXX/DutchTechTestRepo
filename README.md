# DutchTechTestRepo

This directory is a standalone Kodi test repository for DutchTech packages on GitHub Pages.

## Initial contents

- `repository.dutchtechtestrepo` (`DutchTechTestRepo`) - version `1.0.0`

The repository starts intentionally empty apart from its repository add-on. Add test add-ons later by dropping their release zip into the repo root and publishing an update.

## Layout

- `repository.dutchtechtestrepo/`: source for the test repository add-on
- `zips/`: generated installable package archives
- `addons.xml`: repository metadata consumed by Kodi
- `addons.xml.md5`: checksum for `addons.xml`
- `scripts/build_repo.py`: full repo publish, including repository version bump
- `scripts/publish_addon_update.py`: import a new addon zip without bumping the repository addon

## Publish workflows

### Full repo publish

```bash
python3 scripts/build_repo.py --base-url https://TechXXX.github.io/DutchTechTestRepo/
```

Use this when you change the repository itself, for example:

- repository metadata or structure
- repository artwork
- repository install flow

This script:

- rebuilds packages and metadata for the whole repo
- bumps `repository.dutchtechtestrepo`
- commits and pushes to `main`

You can also set `KODI_REPO_BASE_URL` instead of passing `--base-url`. Repository metadata defaults to `https://raw.githubusercontent.com/TechXXX/DutchTechTestRepo/main/`.

### Add-on update publish

Drop a new add-on zip in the repo root and run:

```bash
python3 scripts/publish_addon_update.py
```

This script:

- imports the new add-on zip from the repo root
- replaces the matching unpacked add-on source directory
- rebuilds only that add-on package under `zips/<addon-id>/`
- regenerates `addons.xml` and `addons.xml.md5`
- commits and pushes to `main`

## Publish

1. Push this directory to `TechXXX/DutchTechTestRepo`.
2. Enable GitHub Pages for the repository.
3. Rebuild with your real GitHub Pages URL.
4. Download the current `repository.dutchtechtestrepo-<version>.zip` from the site in a browser.
5. Install that local zip file in Kodi.

The repository add-on itself is configured to fetch metadata and zips from `https://raw.githubusercontent.com/TechXXX/DutchTechTestRepo/main/`.

## Important note about GitHub Pages

GitHub Pages serves direct files but does not expose a browsable directory listing for `zips/`.
That means Kodi will not show hosted zip files when you browse a GitHub Pages source in `Install from zip file`.

Use this flow instead:

1. Download the current `repository.dutchtechtestrepo-<version>.zip` directly from the site.
2. In Kodi, install that local zip file.
3. Then use `Install from repository` for `DutchTechTestRepo`.
