"""
core/vectorize.py
"""

import cv2
import numpy as np
from PIL import Image, ImageEnhance
import io
import base64
from enum import Enum


class VectorMode(str, Enum):
    OUTLINE    = "outline"
    CENTERLINE = "centerline"


def preprocess(
    img_bgr: np.ndarray,
    smoothing: int = 1,
    invert: bool = False,
    brightness: float = 1.0,   # 0.5 = darker, 2.0 = brighter
    contrast: float = 1.0,     # 0.5 = less, 2.0 = more
) -> np.ndarray:
    """
    Convert a color capture to a clean binary image (255 = ink, 0 = background).
    """
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # Brightness / contrast via PIL (easier API than OpenCV for this)
    pil = Image.fromarray(gray)
    if brightness != 1.0:
        pil = ImageEnhance.Brightness(pil).enhance(brightness)
    if contrast != 1.0:
        pil = ImageEnhance.Contrast(pil).enhance(contrast)
    gray = np.array(pil)

    if smoothing == 1:
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
    elif smoothing >= 2:
        gray = cv2.GaussianBlur(gray, (5, 5), 0)

    thresh_type = cv2.THRESH_BINARY if invert else cv2.THRESH_BINARY_INV
    binary = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        thresh_type,
        blockSize=31,
        C=8
    )

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    return binary


def vectorize_outline(binary: np.ndarray, smoothing: int = 1) -> list:
    """Returns list of path dicts: {d, area}"""
    contours, _ = cv2.findContours(binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_TC89_KCOS)
    paths = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 10:
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
        paths.append({"d": d, "area": area, "type": "outline"})
    return paths


def vectorize_centerline(binary: np.ndarray, smoothing: int = 1) -> list:
    """Returns list of path dicts: {d, area}"""
    try:
        skel = cv2.ximgproc.thinning(binary, thinningType=cv2.ximgproc.THINNING_ZHANGSUEN)
    except AttributeError:
        skel = _morphological_skeleton(binary)

    lines = _trace_skeleton(skel, smoothing)
    paths = []
    for line in lines:
        if len(line) < 2:
            continue
        d = f"M {line[0][0]:.2f} {line[0][1]:.2f} "
        d += " ".join(f"L {x:.2f} {y:.2f}" for x, y in line[1:])
        paths.append({"d": d, "area": len(line), "type": "centerline"})
    return paths


def paths_to_svg(paths: list, w: int, h: int, scale: float = 1.0,
                  phys_w_mm: float = 0, phys_h_mm: float = 0) -> str:
    """
    Convert path list to SVG string.
    w, h       : image pixel dimensions (path coords are in these units)
    scale      : output scale multiplier
    phys_w_mm  : real-world width of capture area in mm
    phys_h_mm  : real-world height of capture area in mm

    The SVG viewBox uses pixel coords (so paths render correctly).
    The SVG width/height are set in mm (so Inkscape + laser software
    import at the correct physical size, and the measure tool is accurate).
    """
    # Physical output size in mm (scaled)
    out_w_mm = phys_w_mm * scale if phys_w_mm else w * scale * 25.4 / 150
    out_h_mm = phys_h_mm * scale if phys_h_mm else h * scale * 25.4 / 150

    els = []
    for i, p in enumerate(paths):
        if p["type"] == "outline":
            els.append(f'  <path id="p{i}" d="{p["d"]}" fill="black" stroke="none"/>')
        else:
            els.append(
                f'  <path id="p{i}" d="{p["d"]}" fill="none" stroke="black" '
                f'stroke-width="1.5" stroke-linecap="round"/>'
            )
    # viewBox uses raw pixel coords; width/height use mm so physical size is correct
    group = f'  <g>\n' + "\n".join(els) + "\n  </g>"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{out_w_mm:.4f}mm" height="{out_h_mm:.4f}mm" '
        f'viewBox="0 0 {w} {h}">\n'
        + group + "\n</svg>"
    )


def _morphological_skeleton(binary):
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


def _trace_skeleton(skel, smoothing=1):
    h, w = skel.shape
    visited = np.zeros((h, w), dtype=bool)
    lines   = []
    neighbors_8 = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]

    def get_unvisited(y, x):
        return [(y+dy, x+dx) for dy, dx in neighbors_8
                if 0<=y+dy<h and 0<=x+dx<w and skel[y+dy,x+dx]>0 and not visited[y+dy,x+dx]]

    ys, xs = np.where(skel > 0)
    for sy, sx in zip(ys, xs):
        if visited[sy, sx]:
            continue
        line, stack = [], [(sy, sx)]
        while stack:
            y, x = stack.pop()
            if visited[y, x]: continue
            visited[y, x] = True
            line.append((x, y))
            stack.extend(get_unvisited(y, x))
        if len(line) >= 2:
            if smoothing >= 1:
                line = _smooth_polyline(line, 3)
            lines.append(line)
    return lines


def _smooth_polyline(pts, window=3):
    if len(pts) < window * 2: return pts
    arr = np.array(pts, dtype=float)
    half = window // 2
    smoothed = arr.copy()
    for i in range(half, len(arr) - half):
        smoothed[i] = arr[i-half:i+half+1].mean(axis=0)
    return [(float(x), float(y)) for x, y in smoothed]


def img_to_base64(img_bgr, fmt="png"):
    rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    pil = Image.fromarray(rgb)
    buf = io.BytesIO()
    pil.save(buf, format=fmt.upper())
    return f"data:image/{fmt};base64," + base64.b64encode(buf.getvalue()).decode()


def binary_to_base64(binary):
    buf = io.BytesIO()
    Image.fromarray(binary).save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
