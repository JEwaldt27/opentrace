"""
core/detect.py

Two detection modes:

  FRAME mode  — physical 3D printed frame
    Capture area: 215.9 x 279.4 mm (8.5" x 11")
    Markers are on the frame border, 3mm from inner capture edge
    Pad size: 24mm, pad center is 15mm outside capture corner

  PAPER mode  — printable marker sheet
    User prints marker_sheet.pdf, places sketch on top
    Markers are printed IN the corners of an 8.5x11 sheet
    Capture area is inset 25mm from each marker center
    (markers live in a 20mm corner region, capture starts after)
"""

import cv2
import numpy as np
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class DetectMode(str, Enum):
    FRAME = "frame"
    PAPER = "paper"


# ── Shared ────────────────────────────────────────────────────
OUTPUT_DPI    = 150

# ── Frame mode constants (mm) ─────────────────────────────────
FRAME_CAPTURE_W = 215.9
FRAME_CAPTURE_H = 279.4
FRAME_PAD_SIZE  = 24.0
FRAME_PAD_MARGIN = 3.0
# Distance from pad center to capture corner = PAD_MARGIN + PAD_SIZE/2
FRAME_PAD_TO_CORNER = FRAME_PAD_MARGIN + FRAME_PAD_SIZE / 2  # 15mm

# ── Paper mode constants (mm) ─────────────────────────────────
# Full sheet is 215.9 x 279.4mm. Markers printed in corners.
# Marker print size: 20x20mm. Center is 15mm from each edge.
# Capture area starts 25mm in from each edge (5mm past marker center).
PAPER_SHEET_W   = 215.9
PAPER_SHEET_H   = 279.4
PAPER_MARKER_MM = 20.0          # printed marker size
PAPER_CENTER_FROM_EDGE = 15.0   # marker center from sheet edge
PAPER_CAPTURE_INSET    = 25.0   # capture area inset from sheet edge
PAPER_CAPTURE_W = PAPER_SHEET_W - PAPER_CAPTURE_INSET * 2   # 165.9mm
PAPER_CAPTURE_H = PAPER_SHEET_H - PAPER_CAPTURE_INSET * 2   # 229.4mm


def mm_to_px(mm, dpi=OUTPUT_DPI):
    return mm * dpi / 25.4


@dataclass
class DetectionResult:
    success: bool
    image: Optional[np.ndarray] = None
    debug_image: Optional[np.ndarray] = None
    marker_ids_found: list = field(default_factory=list)
    error: str = ""
    mode: str = ""


def detect_and_correct(img_bgr: np.ndarray, mode: DetectMode = DetectMode.FRAME) -> DetectionResult:
    aruco_dict   = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    aruco_params = cv2.aruco.DetectorParameters()
    detector     = cv2.aruco.ArucoDetector(aruco_dict, aruco_params)

    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    corners, ids, _ = detector.detectMarkers(gray)

    debug = img_bgr.copy()
    if ids is not None:
        cv2.aruco.drawDetectedMarkers(debug, corners, ids)

    if ids is None or len(ids) < 4:
        found = ids.flatten().tolist() if ids is not None else []
        return DetectionResult(
            success=False, debug_image=debug,
            marker_ids_found=found, mode=mode,
            error=f"Only found {len(found)}/4 markers: {found}"
        )

    ids_flat = ids.flatten()
    if not {0,1,2,3}.issubset(set(ids_flat.tolist())):
        missing = {0,1,2,3} - set(ids_flat.tolist())
        return DetectionResult(
            success=False, debug_image=debug,
            marker_ids_found=ids_flat.tolist(), mode=mode,
            error=f"Missing marker IDs: {missing}"
        )

    # Get center of each marker
    id_to_center = {}
    for corner, mid in zip(corners, ids_flat):
        cx = corner[0][:, 0].mean()
        cy = corner[0][:, 1].mean()
        id_to_center[int(mid)] = np.array([cx, cy], dtype=np.float32)

    bl = id_to_center[0]
    br = id_to_center[1]
    tl = id_to_center[2]
    tr = id_to_center[3]

    # Orientation vectors
    right_vec = ((br - bl) + (tr - tl)) / 2
    right_vec /= np.linalg.norm(right_vec)
    up_vec    = ((tl - bl) + (tr - br)) / 2
    up_vec   /= np.linalg.norm(up_vec)

    if mode == DetectMode.FRAME:
        # Capture corners are 15mm inward from each pad center
        offset_px = mm_to_px(FRAME_PAD_TO_CORNER)
        out_w = int(mm_to_px(FRAME_CAPTURE_W))
        out_h = int(mm_to_px(FRAME_CAPTURE_H))
        # Pad centers are OUTSIDE the capture area, so we move inward
        src_tl = tl + offset_px *  right_vec - offset_px * up_vec
        src_tr = tr - offset_px *  right_vec - offset_px * up_vec
        src_bl = bl + offset_px *  right_vec + offset_px * up_vec
        src_br = br - offset_px *  right_vec + offset_px * up_vec

    else:  # PAPER mode
        # Markers are IN the corners of the sheet.
        # Capture area is 25mm inset from sheet edge = 10mm past marker center.
        offset_px = mm_to_px(PAPER_CAPTURE_INSET - PAPER_CENTER_FROM_EDGE)  # 10mm inward
        out_w = int(mm_to_px(PAPER_CAPTURE_W))
        out_h = int(mm_to_px(PAPER_CAPTURE_H))
        # Marker centers are INSIDE the sheet, capture is further inward
        src_tl = tl + offset_px *  right_vec - offset_px * up_vec
        src_tr = tr - offset_px *  right_vec - offset_px * up_vec
        src_bl = bl + offset_px *  right_vec + offset_px * up_vec
        src_br = br - offset_px *  right_vec + offset_px * up_vec

    src_pts = np.array([src_tl, src_tr, src_bl, src_br], dtype=np.float32)
    dst_pts = np.array([
        [0,        0       ],
        [out_w-1,  0       ],
        [0,        out_h-1 ],
        [out_w-1,  out_h-1 ],
    ], dtype=np.float32)

    H, _ = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
    if H is None:
        return DetectionResult(
            success=False, debug_image=debug,
            marker_ids_found=ids_flat.tolist(), mode=mode,
            error="Homography computation failed"
        )

    warped = cv2.warpPerspective(img_bgr, H, (out_w, out_h))

    # Draw capture corners on debug
    for pt in [src_tl, src_tr, src_bl, src_br]:
        cv2.circle(debug, tuple(pt.astype(int)), 8, (0, 255, 0), -1)

    return DetectionResult(
        success=True, image=warped, debug_image=debug,
        marker_ids_found=ids_flat.tolist(), mode=mode
    )
