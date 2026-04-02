* [v3.23.8](https://github.com/newt-sc/a4kSubtitles/releases/tag/service.subtitles.a4ksubtitles%2Fservice.subtitles.a4ksubtitles-3.23.8):
  * Move full release history into CHANGELOG.md so repository metadata stays compact.

* [v3.23.7](https://github.com/newt-sc/a4kSubtitles/releases/tag/service.subtitles.a4ksubtitles%2Fservice.subtitles.a4ksubtitles-3.23.7):
  * Relax OpenSubtitles TV episode IMDb filtering in API-mode pre-play searches so valid episode subtitle results survive to Fenlight matching.

* [v3.23.6](https://github.com/newt-sc/a4kSubtitles/releases/tag/service.subtitles.a4ksubtitles%2Fservice.subtitles.a4ksubtitles-3.23.6):
  * Add targeted search pipeline logging for API-mode pre-play debugging, including raw service results and each prepare/filter stage.

* [v3.23.5](https://github.com/newt-sc/a4kSubtitles/releases/tag/service.subtitles.a4ksubtitles%2Fservice.subtitles.a4ksubtitles-3.23.5):
  * Mock the full video metadata entrypoint in API mode so subtitle probing can run before playback without Kodi player state.

* [v3.23.4](https://github.com/newt-sc/a4kSubtitles/releases/tag/service.subtitles.a4ksubtitles%2Fservice.subtitles.a4ksubtitles-3.23.4):
  * Skip immutable xbmcvfs.File method overrides in live Kodi so API-mode subtitle probing can continue without mocked size/hash methods.

* [v3.23.3](https://github.com/newt-sc/a4kSubtitles/releases/tag/service.subtitles.a4ksubtitles%2Fservice.subtitles.a4ksubtitles-3.23.3):
  * Fix API-mode filename mocking fallback for live Kodi by avoiding Python name-mangling on the internal video helper.

* [v3.23.2](https://github.com/newt-sc/a4kSubtitles/releases/tag/service.subtitles.a4ksubtitles%2Fservice.subtitles.a4ksubtitles-3.23.2):
  * Make API-mode video metadata mocking compatible with live Kodi Player objects.

* [v3.23.1](https://github.com/newt-sc/a4kSubtitles/releases/tag/service.subtitles.a4ksubtitles%2Fservice.subtitles.a4ksubtitles-3.23.1):
  * Fix overwriting existing subtitles during auto-download.

* [v3.23.0](https://github.com/newt-sc/a4kSubtitles/releases/tag/service.subtitles.a4ksubtitles%2Fservice.subtitles.a4ksubtitles-3.23.0):
  * Fix Podnadpisi download handling.
  * Reduce logs verbosity without debug enabled.

* [v3.22.0](https://github.com/newt-sc/a4kSubtitles/releases/tag/service.subtitles.a4ksubtitles%2Fservice.subtitles.a4ksubtitles-3.22.0):
  * Fix Podnadpisi service returning incorrect language codes.

* [v3.21.5](https://github.com/newt-sc/a4kSubtitles/releases/tag/service.subtitles.a4ksubtitles%2Fservice.subtitles.a4ksubtitles-3.21.5):
  * SubSource: Fix language handling so all regional variants are detected instead of only one.

* [v3.21.4](https://github.com/newt-sc/a4kSubtitles/releases/tag/service.subtitles.a4ksubtitles%2Fservice.subtitles.a4ksubtitles-3.21.4):
  * SubSource: Fix foreign language handling in the new API.
  * Metainfo: Fix IMDb release year to correctly pull the first release date for TV shows.

* [v3.21.3](https://github.com/newt-sc/a4kSubtitles/releases/tag/service.subtitles.a4ksubtitles%2Fservice.subtitles.a4ksubtitles-3.21.3):
  * SubSource: Fix and update API (now requires API key)

* [v3.21.2](https://github.com/newt-sc/a4kSubtitles/releases/tag/service.subtitles.a4ksubtitles%2Fservice.subtitles.a4ksubtitles-3.21.2):
  * SubSource: Fix and update API

* [v3.21.1](https://github.com/newt-sc/a4kSubtitles/releases/tag/service.subtitles.a4ksubtitles%2Fservice.subtitles.a4ksubtitles-3.21.1):
  * Dynamic AI subtitles translation from English to the selected Preferred Language in KODI's settings
    * Requires API Key
    * Currently only OpenAI and NexosAI backends are supported
    * For NexosAI model should be specified by ID, not name
    * Turning AI translation on - disables usage of embedded subtitles
    * Currently only supported when using auto-search or auto-download feature

* [v3.20.0](https://github.com/newt-sc/a4kSubtitles/releases/tag/service.subtitles.a4ksubtitles%2Fservice.subtitles.a4ksubtitles-3.20.0):
  * Auto download/selection improvements (by bbviking)

* [v3.19.1](https://github.com/newt-sc/a4kSubtitles/releases/tag/service.subtitles.a4ksubtitles%2Fservice.subtitles.a4ksubtitles-3.19.1):
  * Parse subtitles version

* [v3.19.0](https://github.com/newt-sc/a4kSubtitles/releases/tag/service.subtitles.a4ksubtitles%2Fservice.subtitles.a4ksubtitles-3.19.0):
  * Lower OpenSubtitles token cache from 7 days to 1 day
  * Fix auto download stopping after first failed subtitle download
  * Fix wrong language set for results when multiple languages are configured (Thanks to @peno64)
