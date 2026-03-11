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

## Project Structure

```
opentrace/
├── main.py              # FastAPI server
├── launch.bat           # Windows launcher
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
