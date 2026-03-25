# Changelog

## [Unreleased]

## [2026.1] - 2026-03-25

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

### Fixed
- Bitrate box overflowing the dialog width — Quality and Bitrate moved to their own row
- Removed deprecated `mov` codec

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
