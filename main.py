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
from core.vectorize import (
    preprocess, vectorize_outline, vectorize_centerline,
    img_to_base64, binary_to_base64, VectorMode
)

app = FastAPI(title="OpenTrace", version="0.1.0")
app.mount("/static", StaticFiles(directory="static"), name="static")
BASE_DIR = Path(__file__).parent


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse((BASE_DIR / "static" / "index.html").read_text(encoding="utf-8"))


@app.post("/api/process")
async def process_image(
    file:       UploadFile = File(...),
    mode:       str = Form("outline"),
    smoothing:  int = Form(1),
    detect_mode: str = Form("frame"),   # "frame" or "paper"
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
            "success": False,
            "error": result.error,
            "markers_found": result.marker_ids_found,
            "debug_image": debug_b64,
        })

    binary = preprocess(result.image, smoothing=smoothing)

    if VectorMode(mode) == VectorMode.CENTERLINE:
        svg = vectorize_centerline(binary, smoothing=smoothing)
    else:
        svg = vectorize_outline(binary, smoothing=smoothing)

    from core.detect import (
        FRAME_CAPTURE_W, FRAME_CAPTURE_H,
        PAPER_CAPTURE_W, PAPER_CAPTURE_H
    )
    cw = FRAME_CAPTURE_W if dm == DetectMode.FRAME else PAPER_CAPTURE_W
    ch = FRAME_CAPTURE_H if dm == DetectMode.FRAME else PAPER_CAPTURE_H

    return JSONResponse({
        "success":       True,
        "markers_found": result.marker_ids_found,
        "debug_image":   debug_b64,
        "preview_image": img_to_base64(result.image),
        "binary_image":  binary_to_base64(binary),
        "svg":           svg,
        "width_mm":      cw,
        "height_mm":     ch,
        "detect_mode":   detect_mode,
    })


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
