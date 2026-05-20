from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


def _normalize(arr: np.ndarray) -> np.ndarray:
    lo, hi = float(arr.min()), float(arr.max())
    if hi - lo < 1e-8:
        return np.zeros_like(arr, dtype=np.float32)
    return ((arr - lo) / (hi - lo)).astype(np.float32)


def _box_from_peak(score_map: np.ndarray, center: tuple[int, int], box_size: int = 64) -> dict:
    h, w = score_map.shape
    cx, cy = center
    half = box_size // 2
    x1, y1 = max(0, cx - half), max(0, cy - half)
    x2, y2 = min(w - 1, cx + half), min(h - 1, cy + half)
    zone = score_map[y1:y2 + 1, x1:x2 + 1]
    strength = float(zone.mean()) if zone.size else 0.0
    return {"x1": int(x1), "y1": int(y1), "x2": int(x2), "y2": int(y2), "strength": max(0.0, min(1.0, strength))}


def run_attention_diagnostics(preview_image_path: Path, text_block_count: int | None = None, region_count: int | None = None) -> dict:
    if not preview_image_path.exists():
        return {
            "heatmap_path": None,
            "primary_focus": None,
            "secondary_focus": [],
            "attention_dispersion": 0.0,
            "visual_noise": 0.0,
            "summary": "Preview image is missing; attention diagnostic could not be generated.",
        }

    image = cv2.imread(str(preview_image_path), cv2.IMREAD_COLOR)
    if image is None:
        return {
            "heatmap_path": None,
            "primary_focus": None,
            "secondary_focus": [],
            "attention_dispersion": 0.0,
            "visual_noise": 0.0,
            "summary": "Preview image could not be decoded.",
        }

    image = cv2.resize(image, (512, 512), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    lap = cv2.Laplacian(gray, cv2.CV_32F)
    local_contrast = cv2.GaussianBlur(np.abs(lap), (0, 0), 2.2)

    edges = cv2.Canny(gray, 80, 180).astype(np.float32) / 255.0
    edge_density = cv2.GaussianBlur(edges, (0, 0), 2.0)

    sat = hsv[:, :, 1].astype(np.float32) / 255.0
    sat_blur = cv2.GaussianBlur(sat, (0, 0), 3.0)
    sat_contrast = np.abs(sat - sat_blur)

    yy, xx = np.mgrid[0:512, 0:512].astype(np.float32)
    cx, cy = 255.5, 255.5
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    centrality = 1.0 - _normalize(d)

    score = 0.34 * _normalize(local_contrast) + 0.31 * _normalize(edge_density) + 0.2 * _normalize(sat_contrast) + 0.15 * centrality

    if text_block_count is not None:
        score += min(0.08, text_block_count / 100.0)
    if region_count is not None:
        score += min(0.07, region_count / 120.0)
    score = _normalize(score)

    flat_idx = np.argsort(score.ravel())[::-1]
    h, w = score.shape
    peaks = []
    used = np.zeros_like(score, dtype=np.uint8)
    for idx in flat_idx[:1500]:
        y, x = divmod(int(idx), w)
        if used[y, x]:
            continue
        peaks.append((x, y))
        cv2.circle(used, (x, y), 50, 1, -1)
        if len(peaks) >= 3:
            break

    primary_focus = _box_from_peak(score, peaks[0]) if peaks else None
    secondary_focus = [_box_from_peak(score, p) for p in peaks[1:]]

    threshold = float(np.quantile(score, 0.85))
    salient_ratio = float((score >= threshold).mean())
    attention_dispersion = max(0.0, min(1.0, salient_ratio))

    edge_raw = float(edges.mean())
    sat_raw = float(sat.std())
    visual_noise = max(0.0, min(1.0, 0.65 * edge_raw + 0.35 * sat_raw))

    heat = cv2.applyColorMap((score * 255).astype(np.uint8), cv2.COLORMAP_JET)
    overlay = cv2.addWeighted(image, 0.52, heat, 0.48, 0)

    out_name = f"{preview_image_path.stem}_attention_overlay{preview_image_path.suffix or '.jpg'}"
    out_path = preview_image_path.with_name(out_name)
    cv2.imwrite(str(out_path), overlay)

    summary = (
        f"Primary focus centered near ({primary_focus['x1']},{primary_focus['y1']}) with "
        f"dispersion {attention_dispersion:.2f} and visual noise {visual_noise:.2f}."
        if primary_focus
        else "No stable focus peak detected."
    )

    return {
        "heatmap_path": out_path,
        "primary_focus": primary_focus,
        "secondary_focus": secondary_focus,
        "attention_dispersion": attention_dispersion,
        "visual_noise": visual_noise,
        "summary": summary,
    }
