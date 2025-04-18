# Notch Command Line Render Plugin for Deadline

A Deadline submission plugin for rendering Notch (.dfx) files using the Notch Command Line Renderer.

## Features

- Support for Notch 1.0 Command Line Renderer
- Multiple output codec options (notchlc, h264, h265, hap, mov, exr, png, jpg, tga, tiff)
- Frame range rendering with configurable chunk sizes
- Individual frame export support for image sequences
- Resolution control (up to 16384x16384)
- Configurable quality and bitrate settings
- Custom layer rendering support
- Comprehensive path validation and sanitization
- Automatic file cleanup
- Windows UNC path support
- Detailed logging system

## Supported File Formats

### Input
- Notch Scene Files (.dfx)

### Output
- NotchLC Single Frame Sequences:
  - MOV (notchlc)
- Video Formats:
  - MOV (notchlc, hap, mov codecs)
  - MP4 (h264, h265 codecs)
- Image Sequences:
  - EXR (.exr)
  - PNG (.png)
  - JPEG (.jpg, .jpeg)
  - TGA (.tga)
  - TIFF (.tif, .tiff)

## Requirements

- Windows operating system
- Notch 1.0 or higher installed
- Codemeter 8.20a or higher installed
- A Notch 1.0 VFX or RFX License
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

2. Ensure the Notch Command Line Renderer is installed in the default location or update the path in `NotchCmdRender.param`

## Configuration

The plugin can be configured through `NotchCmdRender.param`:

- `RenderExecutable`: Path to the NotchCmdLineRender.exe
- `TempDir`: Optional custom temporary directory for intermediate files

## Usage

1. Launch Deadline Monitor
2. Click "Submit Job"
3. Select "Notch NURA Job Submission"
4. Fill in the required fields:
   - Job Name
   - Worker Pool
   - Scene File (.dfx)
   - Output Folder and Filename
   - Codec Type
   - Resolution
   - Frame Range
   - FPS
   - Quality/Bitrate (optional)
   - Refines (optional)
   - Layer (optional)
   - Log File (optional)
5. Click "Submit" to send the job to Deadline

## Features in Detail

### Individual Frames Mode
- Automatically enabled for image codecs (exr, png, jpg, tga, tiff)
- Appends frame numbers to filenames
- Sets chunk size to 1 for optimal distribution

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

## Support

For issues related to:
- Plugin functionality: Check Deadline Monitor logs
- Render errors: Check the specified log file or Notch render logs
- Configuration: Review NotchCmdRender.param settings

## License

This plugin is written by Antony Bailey on behalf of 10bit FX Ltd.