# OpenTrace

Open source sketch-to-SVG tool — a free alternative to Shaper Trace.

## Requirements

- Windows 10/11
- Python 3.10 or newer → https://www.python.org/downloads/
  - ✅ Check "Add Python to PATH" during install

## Quick Start

1. Double-click `launch.bat`
2. First run will install dependencies automatically
3. Browser opens to http://localhost:8000

## Usage

1. **Camera mode**: Click "Start Camera", hold your phone/webcam over the frame, click Capture
2. **Upload mode**: Take a photo on your phone, transfer it, then drag & drop or click to upload
3. Choose **Outline** (for cutting) or **Centerline** (for engraving/routing)
4. Adjust **Smoothing** if lines are too jagged or too rounded
5. Click **Process Image**
6. Download your SVG from the bottom bar

## Building the EXE

To produce a standalone `dist\OpenTrace\` folder that requires no Python install:

1. Run `build.bat` (or paste the pyinstaller command from it into a terminal)
2. Output lands in `dist\OpenTrace\OpenTrace.exe`
3. Zip the entire `dist\OpenTrace\` folder to share it

## Project Structure

```
opentrace/
├── main.py              # FastAPI server
├── launch.bat           # Run from source (Windows)
├── build.bat            # PyInstaller build script
├── requirements.txt     # Python dependencies
├── core/
│   ├── detect.py        # ArUco detection + perspective correction
│   └── vectorize.py     # Image processing + SVG generation
└── static/
    └── index.html       # Web UI
```

## Frame Reference (WIP - FILES POSTED SOON)

- Capture area: 215.9 × 279.4 mm (8.5" × 11")
- Border: 30 mm all sides
- ArUco dictionary: DICT_4X4_50
  - ID 0 = Bottom-Left
  - ID 1 = Bottom-Right
  - ID 2 = Top-Left
  - ID 3 = Top-Right

## Tips

- Good lighting = better detection. Avoid harsh shadows across the frame.
- The camera does NOT need to be directly overhead — the perspective correction handles angles up to ~45°.
- If markers aren't detected, check the Debug View tab to see what the server sees.
- Centerline mode works best for single-stroke drawings. Outline mode works best for thick/filled shapes.

## Changelog

### v0.2.0
- Initial public release
- ArUco marker detection with perspective correction (Frame and Paper Sheet modes)
- Outline and Centerline vectorization modes
- Brightness, contrast, and smoothing controls
- Invert toggle for light ink on dark paper
- Manual crop with drag-to-select on the Corrected tab
- Per-path deletion with undo stack
- Scale multiplier with presets (0.5×, 1×, 2×, 3×, custom)
- SVG download and clipboard copy

### v0.2.1
- Fixed SVG `width`/`height` attributes to use real mm dimensions instead of pixels — SVGs now import at correct physical size in Inkscape and laser software
- Added **📏 Measure Tool** — click two points on the SVG to measure the real-world distance in mm and inches
- Added **⇲ Autoscale** — place two measure points on a known reference line in your sketch, enter the true distance, and the SVG rescales automatically. Accepts `1in`, `25.4mm`, or bare numbers (mm assumed)
- Added **zoom and pan** in the SVG tab — scroll wheel to zoom toward cursor, `+`/`−`/reset buttons in the corner, middle-mouse drag to pan
- Path deletion is now blocked while measure mode is active to prevent accidental deletes
- Frame mode temporarily disabled — Paper Sheet mode only for now while the physical frame is still in development
