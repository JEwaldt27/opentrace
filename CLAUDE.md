# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the server

```bash
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Install dependencies:
```bash
pip install -r requirements.txt
```

There are no tests. There is no linter configuration.

## Building the EXE

`build.bat` produces a standalone `dist\OpenTrace\` folder using PyInstaller (`--onedir`). Run it from the project root — it installs PyInstaller automatically, builds, then cleans up the `build\` folder and `.spec` file. The whole `dist\OpenTrace\` folder must be distributed together (zip it to share).

Key PyInstaller considerations:
- `--collect-all cv2` is required to bundle all OpenCV DLLs and data files
- Several `--hidden-import uvicorn.*` flags are needed because PyInstaller misses uvicorn's dynamic imports
- `main.py` uses `sys._MEIPASS` to resolve `BASE_DIR` and the `StaticFiles` mount path when frozen — do not change these to relative paths
- `main.py` has a `__main__` block that calls `uvicorn.run()` directly and auto-opens the browser, which is what the EXE uses as its entry point

## Architecture

OpenTrace is a **local-only** FastAPI app — the Python backend serves both the API and the single-page frontend (`static/index.html`). All processing happens server-side; the browser never touches OpenCV.

### Request flow

1. Browser posts an image + form params to `POST /api/process`
2. `core/detect.py` — detects 4 ArUco markers (DICT_4X4_50, IDs 0–3), computes a homography, and returns a perspective-corrected image
3. `core/vectorize.py` — preprocesses the corrected image to binary, then vectorizes to a list of path dicts `{d, area, type}`
4. `main.py` assembles the SVG and returns JSON with `svg`, `paths`, preview images (base64), and physical dimensions in mm
5. The UI renders the SVG and allows per-path deletion; deletions are applied client-side and the rebuilt SVG is fetched via `POST /api/rebuild-svg` (no reprocessing)

### Detection modes (`core/detect.py`)

| Mode | Physical setup | Capture area |
|------|---------------|--------------|
| `FRAME` | 3D-printed physical frame | 215.9 × 279.4 mm |
| `PAPER` | Printed marker sheet placed under sketch | 165.9 × 229.4 mm |

Perspective correction uses `cv2.findHomography` + `cv2.warpPerspective`. Marker layout: ID 0 = BL, 1 = BR, 2 = TL, 3 = TR.

### Vectorization modes (`core/vectorize.py`)

- **Outline** — `cv2.findContours` → `cv2.approxPolyDP` → closed filled paths (best for thick shapes)
- **Centerline** — Zhang-Suen thinning (`cv2.ximgproc.thinning`, falls back to morphological skeleton) → `_trace_skeleton` → open stroked paths (best for single-stroke drawings)

### SVG coordinate system

Path coordinates are in **image pixels**; the SVG `viewBox` uses these directly. The SVG `width`/`height` attributes are set in **mm** (derived from the known physical capture area) so the file imports at correct physical size in Inkscape and laser software.

### Frontend (`static/index.html`)

Single self-contained HTML file with no build step and no external dependencies. Contains all JS inline. Key client-side state: the `paths` array returned by the server, which the UI mutates for per-path deletion (with an undo stack), then POSTs back to `/api/rebuild-svg`.
