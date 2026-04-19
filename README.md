# DutchTechTestRepo

This repository is the GitHub Pages test repo for DutchTech Kodi packages.

For the subtitle-selector migration, this repo matters because it is the test
distribution channel for the patched Fenlight and patched a4k addons. It also
now carries two Gemini-backed AI-search surfaces:

- the standalone `plugin.video.fenlight.aisearch` fork
- the in-addon AI Search entrypoint inside `plugin.video.fenlight.patched`

## Addons In This Repo

Current source-tree versions when this document was updated:

- `plugin.video.fenlight` `2.0.13`
  Baseline Fenlight package.
- `plugin.video.fenlight.aisearch` `1.0.4`
  Standalone AI-search fork with its own addon id, profile, artwork, and repo package. It now also preserves named people separately from loose keywords so movie prompts can drive TMDb cast-aware discovery.
- `plugin.video.fenlight.patched` `2.0.35`
  Test build that bundles the selector locally and uses the centralized
  subtitle-aware retry-pool architecture. It now also includes an in-addon
  Gemini-backed AI Search entrypoint that still renders TMDb-backed lists and
  now keeps named-person intent available for cast-aware movie discovery.
- `service.subtitles.a4ksubtitles` `3.23.8`
  Baseline a4k package kept as reference.
- `service.subtitles.a4ksubtitles.patched` `3.23.26`
  Test subtitle addon used with selector-aware Fenlight.
- `service.kodi.synctool` `0.2.39`
  Separate Google Drive sync addon that is unrelated to subtitle-selector work.
- `repository.dutchtechtestrepo` `1.0.6`
  The repository addon that Kodi installs first.

## Layout

- `plugin.video.fenlight.patched/`
  Unpacked patched Fenlight source.
- `plugin.video.fenlight.aisearch/`
  Standalone Fenlight AI Search fork.
- `service.subtitles.a4ksubtitles.patched/`
  Unpacked patched a4k source.
- `plugin.video.fenlight/`
  Baseline Fenlight source for comparison or non-patched shipping.
- `service.subtitles.a4ksubtitles/`
  Baseline a4k source for comparison or non-patched shipping.
- `service.kodi.synctool/`
  Unrelated sync addon.
- `scripts/`
  Repo build and publish helpers.
- `zips/`
  Generated installable addon packages. Do not hand-edit these.
- `addons.xml`
  Kodi metadata for every addon in the repo.
- `addons.xml.md5`
  Checksum for `addons.xml`.

## Docs To Read First

For selector or AI-search work in this repo, read:

1. `README.md`
2. `scripts/README.md`
3. `plugin.video.fenlight.patched/resources/lib/modules/ai_search.md`
4. `plugin.video.fenlight.patched/resources/lib/modules/sources.md`
5. `plugin.video.fenlight.patched/resources/lib/modules/player.md`
6. `service.subtitles.a4ksubtitles.patched/README.md`

## Selector-Relevant Addon Responsibilities

### `plugin.video.fenlight.patched`

This addon now owns:

- source scraping and filtering
- one-shot subtitle gather orchestration
- selector-backed retry-pool promotion
- TMDb-backed AI Search result building from Gemini prompt interpretation
- playback resolution and player handoff

It should not own the actual subtitle policy rules. Those belong in the
selector. AI prompt interpretation and result-building also belong in
`modules/ai_search.py`, not in `sources.py` or `player.py`.

### `service.subtitles.a4ksubtitles.patched`

This addon now owns:

- subtitle provider queries
- OpenSubtitles translation-flag capture
- subtitle ordering on the addon side
- manual-search UI badges like `[AI]` and `[MT]`
- translated-subtitle fallback notifications when a subtitle is actually chosen

It should not own Fenlight playback logic.

## Script Workflows

The scripts are documented in `scripts/README.md`.

Short version:

- use `scripts/build_repo.py` when the repository addon itself or the overall
  repo metadata changes
- use `scripts/publish_addon_update.py` when publishing a packaged addon update
  without bumping the repository addon version

Important future-agent nuance:

- the `publish_addon_update.py` command-line flow is built around the "drop a
  new addon zip in the repo root" workflow
- if you have already edited the unpacked source tree in place, you may need to
  call that script's helper functions or regenerate `zips/<addon-id>/`
  manually instead of relying on the CLI import step

## Generated Output Rules

- treat `zips/` as generated output
- if addon-local docs change, regenerate the matching package under `zips/`
- if `addon.xml` changes, also regenerate `addons.xml`
- do not edit `addons.xml.md5` by hand

## Scope Guard Rails

- subtitle-selector migration work belongs primarily in:
  - `plugin.video.fenlight.patched`
  - `service.subtitles.a4ksubtitles.patched`
- in-addon AI Search work for patched Fenlight belongs primarily in:
  - `plugin.video.fenlight.patched/resources/lib/modules/ai_search.py`
  - its router, settings-cache, settings-manager, and search-history wiring
- baseline addons are reference points, not the main landing zone for new
  selector behavior
- unrelated addons such as `service.kodi.synctool` should only be touched when
  intentionally working on that addon
