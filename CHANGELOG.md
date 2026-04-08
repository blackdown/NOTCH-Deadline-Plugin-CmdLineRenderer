# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

## [2026.1.3] - 2026-04-08
> Targets Notch 2026.1 Build 1.0.0.210 (8th April 2026)
> Release notes: https://manual.notch.one/2026.1/en/docs/whats-new/release-notes/1-0-0/#20261-build-100210-8th-april-2026

### Added
- `-stdout 1` always passed automatically for headless farm operation
- `-autopreroll 0|1` — auto pre-roll toggle, enabled by default (checkbox in dialog)
- `-prerollstart` — pre-roll duration in seconds (matches Pre-Roll parameter in Builder)
- `-tiled 0|1` — tiled rendering for large canvas sizes that won't fit in GPU buffer
- `-tilesize` — tile size in pixels (requires tiled enabled; 2048–4096px recommended for Path Tracer)
- `-overscan` — overscan in pixels per tile for seamless blending in post (requires tiled enabled)
- `-metadata filename` — export render metadata to a JSON file
- `-debug 0|1` — extra logging, disabled by default

### Changed
- Expanded colour space options to match Notch Builder: added `p3linear`, `dcip3`, `p3d65`, `rec2020`, `p3display`, `rec709`
- Updated README with all new flags, expanded feature list, and updated usage guide

## [2026.1.2] - 2026-03-28

### Changed
- Removed automatic `-still` flag based on codec type — it disabled motion blur and temporal effects on image sequences, which was incorrect
- `-still` is now user-controlled via a "Still Image" checkbox (unchecked by default) and should only be used for a true static image with no temporal processing required

## [2026.1.1] - 2026-03-25

### Fixed
- Image codec farm tasks incorrectly used the full stored frame range instead of the current task frame, causing all workers to overwrite the same output file
- Bitrate box overflowing the dialog width — Quality and Bitrate moved to their own row

---

## [2026.1.0] - 2026-03-25

### Changed
- Renamed executable from `NotchCmdLineRender.exe` to `NotchRenderNodeCLI.exe` (install folder remains `Notch 1.0`)
- Fixed CLI flag casing to match new renderer: `-startframe`, `-endframe`, `-width`, `-height`, `-codec`
- Renamed `tiff` codec to `tif` to match new CLI naming
- Replaced extension-based still image detection with the explicit `-still` flag
- Updated documentation URL to Notch 2026.1 reference
- Updated license requirement wording: VFX/RFX or dedicated Render Node License

### Added
- New codec options: `hapa` (HAP Alpha) and `hapq` (HAPQ)
- New optional render flags: `-layername`, `-gpu`, `-colourspace`, `-aov`
- Layer Name, GPU, Colour Space, and AOV fields in the submission dialog
- Unit test suite (`tests/test_render_argument.py`) — runs without Deadline or Notch installed

### Removed
- `mov` codec (no longer supported by the Notch Render Node CLI)

---

## [1.0.0] - Initial Release

### Added
- Deadline submission plugin for Notch (.dfx) scene files using `NotchCmdLineRender.exe`
- Support for codecs: notchlc, h264, h265, hap, mov, exr, png, jpeg, tga, tiff
- Individual frame export mode for image sequences and notchlc codec
- Real-time filename preview in submission dialog
- Resolution, FPS, quality, bitrate, refines, and layer controls
- Log file monitoring via background thread
- Comprehensive path validation and sanitization
- Windows UNC path support
- Automatic temporary file cleanup
