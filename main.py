"""
main.py  —  OpenTrace local server
"""

import cv2
import numpy as np
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from core.detect import detect_and_correct, DetectMode
from core.detect import FRAME_CAPTURE_W, FRAME_CAPTURE_H, PAPER_CAPTURE_W, PAPER_CAPTURE_H
from core.vectorize import (
    preprocess, vectorize_outline, vectorize_centerline,
    paths_to_svg, img_to_base64, binary_to_base64, VectorMode
)

app = FastAPI(title="OpenTrace", version="0.2.0")
app.mount("/static", StaticFiles(directory="static"), name="static")
BASE_DIR = Path(__file__).parent


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse((BASE_DIR / "static" / "index.html").read_text(encoding="utf-8"))


@app.post("/api/process")
async def process_image(
    file:         UploadFile = File(...),
    mode:         str   = Form("outline"),
    smoothing:    int   = Form(1),
    detect_mode:  str   = Form("frame"),
    invert:       bool  = Form(False),
    brightness:   float = Form(1.0),
    contrast:     float = Form(1.0),
    scale:        float = Form(1.0),
    crop_x:       float = Form(0),      # crop rect in px (0 = no crop)
    crop_y:       float = Form(0),
    crop_w:       float = Form(0),
    crop_h:       float = Form(0),
):
    raw   = await file.read()
    nparr = np.frombuffer(raw, np.uint8)
    img   = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        return JSONResponse({"success": False, "error": "Could not decode image"}, status_code=400)

    dm     = DetectMode.PAPER if detect_mode == "paper" else DetectMode.FRAME
    result = detect_and_correct(img, mode=dm)
    debug_b64 = img_to_base64(result.debug_image) if result.debug_image is not None else ""

    if not result.success:
        return JSONResponse({
            "success": False, "error": result.error,
            "markers_found": result.marker_ids_found,
            "debug_image": debug_b64,
        })

    corrected = result.image

    # Apply crop if provided
    if crop_w > 0 and crop_h > 0:
        ih, iw = corrected.shape[:2]
        x1 = max(0, int(crop_x))
        y1 = max(0, int(crop_y))
        x2 = min(iw, int(crop_x + crop_w))
        y2 = min(ih, int(crop_y + crop_h))
        corrected = corrected[y1:y2, x1:x2]

    binary = preprocess(corrected, smoothing=smoothing, invert=invert,
                        brightness=brightness, contrast=contrast)

    if VectorMode(mode) == VectorMode.CENTERLINE:
        paths = vectorize_centerline(binary, smoothing=smoothing)
    else:
        paths = vectorize_outline(binary, smoothing=smoothing)

    ih, iw = binary.shape

    cw = FRAME_CAPTURE_W if dm == DetectMode.FRAME else PAPER_CAPTURE_W
    ch = FRAME_CAPTURE_H if dm == DetectMode.FRAME else PAPER_CAPTURE_H
    if crop_w > 0 and corrected.shape[1] > 0 and corrected.shape[0] > 0:
        full_iw = result.image.shape[1]
        full_ih = result.image.shape[0]
        cw = round(cw * (crop_w / full_iw), 2)
        ch = round(ch * (crop_h / full_ih), 2)

    svg = paths_to_svg(paths, iw, ih, scale=scale, phys_w_mm=cw, phys_h_mm=ch)

    return JSONResponse({
        "success":       True,
        "markers_found": result.marker_ids_found,
        "debug_image":   debug_b64,
        "preview_image": img_to_base64(corrected),
        "binary_image":  binary_to_base64(binary),
        "svg":           svg,
        "paths":         paths,          # sent back so UI can do live delete
        "img_w":         iw,
        "img_h":         ih,
        "width_mm":      round(cw * scale, 1),
        "height_mm":     round(ch * scale, 1),
        "detect_mode":   detect_mode,
    })


@app.post("/api/rebuild-svg")
async def rebuild_svg(
    paths_json: str  = Form(...),
    img_w:      int  = Form(...),
    img_h:      int  = Form(...),
    scale:      float = Form(1.0),
):
    """Rebuild SVG from a (possibly path-deleted) paths list without reprocessing."""
    import json
    paths = json.loads(paths_json)
    svg   = paths_to_svg(paths, img_w, img_h, scale=scale)
    return JSONResponse({"svg": svg, "path_count": len(paths)})


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.2.0"}
