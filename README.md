# DutchTechTestRepo

This repository is the GitHub Pages test repo for DutchTech Kodi packages.

For the subtitle-selector migration, this repo matters because it is the test
distribution channel for the patched Fenlight and patched a4k addons. It also
now carries two Gemini-backed AI-search surfaces and two UI/navigation support
addons:

- the standalone `plugin.video.fenlight.aisearch` fork
- the in-addon AI Search entrypoint inside `plugin.video.fenlight.patched`
- `plugin.video.themoviedb.helper.patched`
- `skin.arctic.horizon.2.patched`

## Progress Snapshot

As of `2026-04-20`, the AI-search work in this repo has moved beyond the first
Gemini MVP:

- `plugin.video.fenlight.patched` source now has the newer AI Search flow that:
  - biases Gemini toward title/franchise interpretation for short prompts
  - keeps named people separate from loose keywords via a `people` field
  - resolves named people through TMDb person search for movie prompts
  - injects `with_cast` into TMDb discover queries when cast intent is present
  - can cycle across up to three Gemini API keys on quota exhaustion
  - uses `v3` AI-search cache keys for fresh interpretation/results
- `plugin.video.fenlight.aisearch` source has been kept in sync with the same
  `v3` AI-search behavior, including multi-key Gemini fallback
- both repo addons also carry the Fen compatibility restore for collection
  search:
  - `plugin://.../?mode=build_movie_list&action=tmdb_movies_search_sets&query=`
- patched Fenlight source now also has the newer selector tuning that:
  - raises the subtitle-backed retry pool from the best `5` to the best `10`
    selector-ranked candidates
  - lets subtitle comment aliases strengthen the same subtitle item when they
    improve the release match instead of being fallback-only in all cases
- patched Fenlight source now also lets the user choose a TMDb metadata
  language plus a fallback language, and fills missing movie/TV/collection/
  season/episode/people details from that fallback before giving up
- Fen also now gets a Trakt auth/rate-limit handling change plus
  subtitle-selector ranking tweaks:
  - bare generic movie-title subtitles are demoted to low-confidence fallbacks
  - low-information source containment hits no longer outrank stronger
    structured DVDRip-style subtitle matches
  - expired Trakt auth now surfaces a clearer notification instead of being
    handled like a generic request failure
- patched TMDb Helper recommendations now normalize keyword/info rows more
  safely and log the recommendation window inputs/actions so the patched AH2
  flow is easier to debug
- patched TMDb Helper also now gets Trakt account-state/settings changes:
  - authenticated Trakt username is stored in settings
  - startup, sync, and connection notifications default to off in test builds
- patched AH2 now clears stale recommendation-window state before opening the
  helper dialog again, reducing reuse of old recommendation properties
- patched AH2 also gets a small cast-bio label improvement so the info dialog
  can still show gender/age/department/birth details when biography text is
  empty
- the current live installed patched addon versions on this machine are:
  - `plugin.video.fenlight.patched` `2.0.36`
  - `service.subtitles.a4ksubtitles.patched` `3.23.27`
  - `plugin.video.themoviedb.helper.patched` `6.15.2.1`
- the live install currently lags this repo for patched Fenlight, patched a4k,
  and patched TMDb Helper, but the core selector-runtime Python files are
  still in sync with this repo for:
  - `plugin.video.fenlight.patched/resources/lib/modules/sources.py`
  - `plugin.video.fenlight.patched/resources/lib/modules/player.py`
  - `plugin.video.fenlight.patched/resources/lib/fenlightsubs/subtitle_selector.py`
  - `service.subtitles.a4ksubtitles.patched/a4kSubtitles/search.py`
  - `service.subtitles.a4ksubtitles.patched/a4kSubtitles/services/opensubtitles.py`
  - `service.subtitles.a4ksubtitles.patched/a4kSubtitles/lib/kodi.py`
- remaining live-vs-test drift is currently in addon versions, changelog text,
  compiled caches, and some Fenlight skin XML files rather than the selector
  handoff core
- repo source-tree verification for the synced AI-search changes passed with:
  - `python3 -m py_compile` on both addon trees
  - `git diff --check`

Important packaging note:

- treat `zips/`, `addons.xml`, and `addons.xml.md5` as generated output
- when these addon source trees change, regenerate the matching package output
  and repo metadata before publish/install testing

## Addons In This Repo

Current source-tree versions when this document was updated:

- `plugin.video.fenlight` `2.0.13`
  Baseline Fenlight package.
- `plugin.video.fenlight.aisearch` `1.0.5`
  Standalone AI-search fork with its own addon id, profile, artwork, and repo package. It now also preserves named people separately from loose keywords so movie prompts can drive TMDb cast-aware discovery.
- `plugin.video.fenlight.patched` `2.0.43`
  Test build that bundles the selector locally and uses the centralized
  subtitle-aware retry-pool architecture. It now also includes an in-addon
  Gemini-backed AI Search entrypoint that still renders TMDb-backed lists and
  now keeps named-person intent available for cast-aware movie discovery. It
  also supports up to three Gemini keys, promotes a larger selector-backed
  retry pool, can request TMDb metadata in a user-selected language with a
  configurable fallback, now carries the newer Trakt handling plus
  subtitle-selector ranking tweaks from the latest test publish, shows an
  explicit Trakt authorization status row in settings, and now skips autoplay
  sources whose detected audio streams are Russian-only, Ukrainian-only, or
  Chinese-only unless the selected title metadata already expects that spoken
  language. It also now uses the show's original or English title plus the
  actual episode name when building TV subtitle-search metadata and filenames.
- `plugin.video.themoviedb.helper.patched` `6.15.2.5`
  Patched TMDb Helper package added to this repo for the matching patched skin
  flow. The current test build also hardens the recommendations window against
  stale keyword/info actions, adds richer debug logging around recommendations
  navigation, persists authenticated Trakt account state more explicitly, and
  now switches OMDb lookups to the JSON endpoint while backfilling missing
  cached IMDb and OMDb ratings more reliably.
- `skin.arctic.horizon.2.patched` `0.8.30.6`
  Patched Arctic Horizon 2 skin package intended to target the patched TMDb
  Helper addon id from this same repo. The current test build also clears stale
  recommendations dialog properties before opening a fresh helper window and
  improves the cast-bio fallback label. It now also ships the Inter font family
  with matching info-panel, rating, and hub-layout refinements, and gives
  Next Page placeholder items dedicated fallback artwork/background handling so
  they stop reusing stray media and plot text.
- `service.subtitles.a4ksubtitles` `3.23.8`
  Baseline a4k package kept as reference.
- `service.subtitles.a4ksubtitles.patched` `3.23.29`
  Test subtitle addon used with selector-aware Fenlight. The current test build
  searches OpenSubtitles TV episodes by parent show IMDb id plus season/episode
  before text fallbacks, so numeric show titles like `1923` return the full
  episode subtitle set for selector ranking.
- `service.kodi.synctool` `0.2.39`
  Separate Google Drive sync addon that is unrelated to subtitle-selector work.
- `repository.dutchtechtestrepo` `1.0.7`
  The repository addon that Kodi installs first.

## Layout

- `plugin.video.fenlight.patched/`
  Unpacked patched Fenlight source.
- `plugin.video.fenlight.aisearch/`
  Standalone Fenlight AI Search fork.
- `plugin.video.themoviedb.helper.patched/`
  Patched TMDb Helper source.
- `skin.arctic.horizon.2.patched/`
  Patched Arctic Horizon 2 skin source.
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

## Handover Prompt

Use this prompt to continue the work in a fresh agent session:

```text
You are continuing work in /Users/kalter/Documents/CODEX/DutchTechTestRepo.

Read /Users/kalter/Documents/CODEX/DutchTechTestRepo/README.md first.

Current important state:
- plugin.video.fenlight.patched and plugin.video.fenlight.aisearch source trees are intended to be in sync for AI Search behavior.
- AI Search is now on a cast-aware v3 flow:
  - stronger short-prompt title/franchise priming
  - Gemini schema includes people
  - movie discover queries can add with_cast after TMDb person lookup
- AI Search can cycle across up to three Gemini API keys on quota exhaustion.
- collection-search compatibility was restored for:
  - plugin://<addon-id>/?mode=build_movie_list&action=tmdb_movies_search_sets&query=
- patched Fenlight subtitle selection now:
  - promotes the best 10 selector-backed retry candidates
  - allows stronger comment aliases to upgrade the same subtitle item
- the current live installed patched addon versions lag this repo for Fenlight, patched a4k, and patched TMDb Helper.
- the current live installed core selector-runtime Python files still match this repo exactly for the Fenlight `sources.py` / `player.py` path, the vendored selector copy, and the patched a4k `search.py` / `opensubtitles.py` / `lib/kodi.py` path.

First steps:
1. Run git status in /Users/kalter/Documents/CODEX/DutchTechTestRepo.
2. Inspect README.md and confirm whether the current task is source-only or publish/install related.
3. If the goal is to ship the newest AI-search or selector changes, regenerate the relevant zips and repo metadata instead of only editing source.
4. Be careful not to overwrite unrelated subtitle-selector work already in plugin.video.fenlight.patched/resources/lib/fenlightsubs/subtitle_selector.py and plugin.video.fenlight.patched/resources/lib/modules/sources.py.

Guard rails:
- Keep plugin.video.fenlight.patched and plugin.video.fenlight.aisearch aligned for AI Search changes unless there is a deliberate reason not to.
- Do not regress the subtitle-selector/subtitle-aware source flow in the patched Fenlight addon.
- Treat zips/ as generated output.
- Prefer minimal, isolated edits and verify with python3 -m py_compile after AI-search changes.
```

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
- the patched TMDb Helper and patched Arctic Horizon 2 skin should stay aligned
  on addon ids and plugin paths if they are shipped as a matched pair from this
  repo
