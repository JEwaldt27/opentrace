"""
core/vectorize.py
Takes a perspective-corrected capture area image and returns SVG paths.

Two modes:
  - outline:    filled shape outlines (good for cutting)
  - centerline: skeleton of the strokes (good for engraving/routing)

No scikit-image dependency — uses opencv-contrib thinning instead.
"""

import cv2
import numpy as np
from PIL import Image
import io
import base64
from enum import Enum


class VectorMode(str, Enum):
    OUTLINE    = "outline"
    CENTERLINE = "centerline"


# ── Step 1: Clean the image ───────────────────────────────────

def preprocess(img_bgr: np.ndarray, smoothing: int = 1) -> np.ndarray:
    """
    Convert a color capture to a clean binary image.
    Returns uint8 array (255 = ink, 0 = background)
    """
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    if smoothing == 1:
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
    elif smoothing >= 2:
        gray = cv2.GaussianBlur(gray, (5, 5), 0)

    binary = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        blockSize=31,
        C=8
    )

    # Remove small noise specks
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

    return binary


# ── Step 2a: Outline vectorization ───────────────────────────

def vectorize_outline(binary: np.ndarray, smoothing: int = 1) -> str:
    h, w = binary.shape
    contours, _ = cv2.findContours(binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_TC89_KCOS)

    paths = []
    for cnt in contours:
        if cv2.contourArea(cnt) < 10:
            continue
        epsilon = smoothing * 0.5
        if epsilon > 0:
            cnt = cv2.approxPolyDP(cnt, epsilon, True)
        pts = cnt.reshape(-1, 2)
        if len(pts) < 2:
            continue
        d = f"M {pts[0][0]:.2f} {pts[0][1]:.2f} "
        d += " ".join(f"L {x:.2f} {y:.2f}" for x, y in pts[1:])
        d += " Z"
        paths.append(f'  <path d="{d}" fill="black" stroke="none"/>')

    return _wrap_svg(w, h, "\n".join(paths))


# ── Step 2b: Centerline vectorization ────────────────────────

def vectorize_centerline(binary: np.ndarray, smoothing: int = 1) -> str:
    h, w = binary.shape

    # Use opencv-contrib thinning (Zhang-Suen) — no scikit-image needed
    # ximgproc is included in opencv-contrib-python
    try:
        skel = cv2.ximgproc.thinning(binary, thinningType=cv2.ximgproc.THINNING_ZHANGSUEN)
    except AttributeError:
        # Fallback: morphological skeleton if ximgproc unavailable
        skel = _morphological_skeleton(binary)

    lines = _trace_skeleton(skel, smoothing)

    path_els = []
    for line in lines:
        if len(line) < 2:
            continue
        d = f"M {line[0][0]:.2f} {line[0][1]:.2f} "
        d += " ".join(f"L {x:.2f} {y:.2f}" for x, y in line[1:])
        path_els.append(
            f'  <path d="{d}" fill="none" stroke="black" '
            f'stroke-width="1.5" stroke-linecap="round"/>'
        )

    return _wrap_svg(w, h, "\n".join(path_els))


def _morphological_skeleton(binary: np.ndarray) -> np.ndarray:
    """Pure OpenCV fallback skeleton using erosion loop."""
    skel = np.zeros_like(binary)
    img  = binary.copy()
    kernel = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
    while True:
        eroded  = cv2.erode(img, kernel)
        dilated = cv2.dilate(eroded, kernel)
        diff    = cv2.subtract(img, dilated)
        skel    = cv2.bitwise_or(skel, diff)
        img     = eroded.copy()
        if cv2.countNonZero(img) == 0:
            break
    return skel


def _trace_skeleton(skel: np.ndarray, smoothing: int = 1):
    """Walk skeleton pixels into polylines using 8-connectivity."""
    h, w = skel.shape
    visited = np.zeros((h, w), dtype=bool)
    lines   = []
    neighbors_8 = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]

    def get_unvisited(y, x):
        result = []
        for dy, dx in neighbors_8:
            ny, nx = y+dy, x+dx
            if 0 <= ny < h and 0 <= nx < w and skel[ny,nx] > 0 and not visited[ny,nx]:
                result.append((ny, nx))
        return result

    ys, xs = np.where(skel > 0)
    for sy, sx in zip(ys, xs):
        if visited[sy, sx]:
            continue
        line  = []
        stack = [(sy, sx)]
        while stack:
            y, x = stack.pop()
            if visited[y, x]:
                continue
            visited[y, x] = True
            line.append((x, y))
            for ny, nx in get_unvisited(y, x):
                stack.append((ny, nx))
        if len(line) >= 2:
            if smoothing >= 1:
                line = _smooth_polyline(line, window=3)
            lines.append(line)

    return lines


def _smooth_polyline(pts, window=3):
    if len(pts) < window * 2:
        return pts
    arr     = np.array(pts, dtype=float)
    half    = window // 2
    smoothed = arr.copy()
    for i in range(half, len(arr) - half):
        smoothed[i] = arr[i-half:i+half+1].mean(axis=0)
    return [(float(x), float(y)) for x, y in smoothed]


def _wrap_svg(w, h, content):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{w}" height="{h}" viewBox="0 0 {w} {h}">\n'
        + content + "\n</svg>"
    )


# ── Utility: image to base64 ──────────────────────────────────

def img_to_base64(img_bgr: np.ndarray, fmt: str = "png") -> str:
    rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    pil = Image.fromarray(rgb)
    buf = io.BytesIO()
    pil.save(buf, format=fmt.upper())
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/{fmt};base64,{b64}"


def binary_to_base64(binary: np.ndarray) -> str:
    pil = Image.fromarray(binary)
    buf = io.BytesIO()
    pil.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return "data:image/png;base64," + b64
