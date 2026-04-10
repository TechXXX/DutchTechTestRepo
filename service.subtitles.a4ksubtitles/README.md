# a4kSubtitles Reference Copy

This directory is the unpacked baseline a4k subtitle addon kept in the test
repo as a comparison point.

It is useful when future agents need to separate:

- upstream-like a4k behavior
- test-repo patch behavior
- selector-migration-specific changes

## Why This Copy Still Matters

Even though selector work should normally land in the patched addon, this
baseline copy is valuable for diffing and rollback analysis.

Typical uses:

- compare search or download behavior against the patched addon
- confirm whether a bug was introduced by the patch set
- understand the original addon structure before repo-specific changes

## Execution Model

The baseline addon follows the same broad shape as the patched copy:

1. `main.py`
   Regular Kodi plugin entrypoint.
2. `main_service.py`
   Background subtitle-service entrypoint.
3. `a4kSubtitles/core.py`
   Routes Kodi actions like `search` and `download`.
4. `a4kSubtitles/search.py`
   Provider auth, search, normalization, filtering, and ordering.
5. `a4kSubtitles/download.py`
   Download and archive extraction logic.
6. `a4kSubtitles/service.py`
   Auto-search / auto-download loop during playback.

## File Map

- `addon.xml`
  Kodi metadata and addon version.
- `main.py`
  Standard plugin execution path.
- `main_service.py`
  Starts the background subtitle service.
- `a4kSubtitles/api.py`
  API bridge for mocked execution and direct search/download calls.
- `a4kSubtitles/core.py`
  Central plugin action router.
- `a4kSubtitles/search.py`
  Provider orchestration and result preparation.
- `a4kSubtitles/download.py`
  File download and extraction flow.
- `a4kSubtitles/service.py`
  Playback-aware automatic subtitle logic.
- `a4kSubtitles/services/opensubtitles.py`
  OpenSubtitles request/response handling.
- `a4kSubtitles/lib/kodi.py`
  Kodi wrappers, settings, and listitem creation.

## How To Use This Copy Safely

- Treat this addon as reference material first.
- Do not land selector-specific behavior here unless you intentionally want the
  baseline package to gain it too.
- When debugging a patch regression, diff this tree against
  `service.subtitles.a4ksubtitles.patched/` before assuming the selector caused
  it.

## What Usually Differs In The Patched Copy

The patched addon is where repo-specific subtitle-selector work lives, such as:

- selector-oriented API-mode use with patched Fenlight
- translation-aware result handling refinements
- manual-search `[AI]` / `[MT]` badges
- selector-migration behavior that is not part of the baseline addon story

If you are unsure where a change belongs, start in the patched copy and only
come back here if you are intentionally aligning the baseline addon too.
