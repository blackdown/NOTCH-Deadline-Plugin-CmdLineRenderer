# Notch Render Node CLI Plugin for Deadline
A [Thinkbox Deadline](https://aws.amazon.com/thinkbox-deadline/) submission plugin for rendering Notch (.dfx) files using the Notch Render Node CLI.

![NURA™ Logo Badge](scripts/Submission/icon.png)

> **Disclaimer:** This is an independent, community-made plugin and is not an official product of Notch or 10bit FX Ltd. It is provided as-is with no warranty or official support.

If this plugin has been useful, consider [buying me a coffee ☕](https://paypal.me/blackdown) — it helps keep projects like this going!

**Last updated: 28 March 2026**

## Features

- Support for Notch 2026.1 Render Node CLI (`NotchRenderNodeCLI.exe`)
- Multiple output codec options (notchlc, h264, h265, hap, hapa, hapq, exr, png, jpeg, tga, tif)
- Frame range rendering with configurable chunk sizes
- Individual frame export support for image sequences and notchlc codec
- Correct per-frame output path construction for distributed farm rendering
- Real-time filename preview showing actual output format
- Resolution control (up to 16384x16384)
- Configurable quality and bitrate settings
- Custom layer rendering by index or name
- GPU selection for multi-GPU render nodes
- Colour space and AOV buffer support
- Comprehensive path validation and sanitization
- Automatic file cleanup
- Windows UNC path support
- Detailed logging system
- Unit test suite for core render argument logic

![Submission Dialogue](readme_files/Submission_Dialog.png)

## Supported File Formats

### Input
- Notch Scene Files (.dfx)

### Output
- NotchLC Single Frame Sequences:
  - MOV (notchlc) with optional individual frame numbering
- Video Formats:
  - MOV (notchlc, hap, hapa, hapq codecs)
  - MP4 (h264, h265 codecs)
- Image Sequences:
  - EXR (.exr)
  - PNG (.png)
  - JPEG (.jpg, .jpeg)
  - TGA (.tga)
  - TIFF (.tif, .tiff)

## Requirements

- Windows operating system
- Notch 2026.1 or higher installed
- Codemeter 8.20a or higher installed
- A Notch VFX or RFX License (or a dedicated Render Node License)
- Deadline Repository and Client
- Valid render pool configuration in Deadline

## Installation

1. Copy the plugin files to your Deadline Repository:
```
  custom/
  ├─ plugins/
  │  └─ NotchCmdRender/
  │     ├─ NotchCmdRender.ico
  │     ├─ NotchCmdRender.param
  │     └─ NotchCmdRender.py
  └─ scripts/
     └─ Submission/
      ├─ icon.png
      └─ NotchCmdRenderSubmission.py
```

2. Ensure the Notch Render Node CLI (`NotchRenderNodeCLI.exe`) is installed in the default location (`C:\Program Files\Notch 1.0\`) or update the path in `NotchCmdRender.param`

## Configuration

The plugin can be configured through `NotchCmdRender.param`:

- `RenderExecutable`: Path to `NotchRenderNodeCLI.exe`
- `TempDir`: Optional custom temporary directory for intermediate files

![Submission Dialogue](readme_files/Settings.png)

## Usage

1. Launch Deadline Monitor
2. Click "Submit Job"
3. Select "Notch NURA Job Submission"
4. Fill in the required fields:
   - Job Name
   - Worker Pool
   - Scene File (.dfx)
   - Output Folder and Filename
   - Individual Frames option (for notchlc codec)
   - Codec Type
   - Resolution
   - Frame Range
   - FPS
   - Quality/Bitrate (optional)
   - Refines (optional)
   - Layer index or Layer Name (optional)
   - GPU (optional, for multi-GPU machines)
   - Colour Space (optional)
   - AOV buffer (optional)
   - Log File (optional)
5. Click "Submit" to send the job to Deadline

![Submission Dialogue](readme_files/RenderQueue.png)

## Features in Detail

### Individual Frames Mode
- Automatically enabled for image codecs (exr, png, jpeg, tga, tif)
- Optional for notchlc codec (user-selectable)
- Disabled for other video codecs (h264, h265, hap, hapa, hapq)
- Each farm task receives the correct single frame and a unique output path
- Appends zero-padded frame numbers to filenames (e.g. `output_0042.png`)
- Sets chunk size to 1 for optimal farm distribution
- Real-time preview of resulting filename format

### Codec-Specific Behaviour
- Image formats (exr, png, jpeg, tga, tif): Always use individual frames, `-still` flag passed automatically
- NotchLC (.mov): Optional individual frames with frame number appending
- Video formats (h264, h265, hap, hapa, hapq): Always single file output, no frame numbering

### New in 2026.1
- Layer Name (`-layername`): Select a composition layer by name instead of index
- GPU (`-gpu`): Pin rendering to a specific GPU adapter — useful on multi-GPU render nodes
- Colour Space (`-colourspace`): Set output colour space (acescg, aces, srgblinear, linear, srgbgamma, gamma)
- AOV (`-aov`): Output a specific render buffer (normal, depth, cryptomatte, uv, objectid, ao, and others)

### Path Validation
- Checks for unsafe characters
- Prevents directory traversal
- Validates file extensions
- Handles UNC paths
- Enforces Windows path length limits

### Error Handling
- Validates all inputs before submission
- Provides detailed error messages
- Retries locked file operations
- Cleans up temporary files
- Logs all operations

### UI
- Interactive filename preview shows actual output format with/without frame numbers
- Codec selection automatically configures related options
- Logical control layout with related options grouped together
- Context-aware controls that enable/disable based on compatibility

## Testing

A unit test suite is included at `tests/test_render_argument.py`. It mocks the Deadline base class so tests can be run on any machine without Deadline or Notch installed:

```
python3 tests/test_render_argument.py
```

## Support

For issues related to:
- Plugin functionality: Check Deadline Monitor logs
- Render errors: Check the specified log file or Notch render logs
- Configuration: Review `NotchCmdRender.param` settings
- Notch CLI reference: https://manual.notch.one/2026.1/en/docs/reference/notchrendernodecli/

## Support the Project

If this plugin has saved you time on a project, a small donation is always appreciated!

[Donate via PayPal](https://paypal.me/blackdown)

## License

This plugin is written by Antony Bailey with the permission of 10bit FX Ltd.
