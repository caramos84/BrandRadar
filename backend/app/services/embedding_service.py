from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image


def _safe_normalize(values: np.ndarray) -> np.ndarray:
    total = float(values.sum())
    if total <= 0:
        return np.zeros_like(values, dtype=np.float32)
    return (values / total).astype(np.float32)


def generate_visual_embedding(image_path: Path) -> list[float]:
    try:
        with Image.open(image_path) as img:
            rgb_img = img.convert("RGB")
            width, height = rgb_img.size
            thumb = rgb_img.resize((128, 128))
            rgb_np = np.asarray(thumb, dtype=np.uint8)
    except Exception:
        return []

    if width <= 0 or height <= 0:
        return []

    features: list[float] = []

    hist_bins = 8
    for channel_idx in range(3):
        channel = rgb_np[:, :, channel_idx]
        hist, _ = np.histogram(channel, bins=hist_bins, range=(0, 256))
        norm_hist = _safe_normalize(hist.astype(np.float32))
        features.extend(norm_hist.tolist())

    channel_means = rgb_np.reshape(-1, 3).mean(axis=0)
    channel_stds = rgb_np.reshape(-1, 3).std(axis=0)
    features.extend((channel_means / 255.0).astype(np.float32).tolist())
    features.extend((channel_stds / 255.0).astype(np.float32).tolist())

    gray = cv2.cvtColor(rgb_np, cv2.COLOR_RGB2GRAY)
    gray_norm = gray.astype(np.float32) / 255.0
    brightness_mean = float(gray_norm.mean())
    brightness_std = float(gray_norm.std())
    features.append(brightness_mean)
    features.append(brightness_std)

    edges = cv2.Canny(gray, 100, 200)
    edge_density = float(np.count_nonzero(edges)) / float(edges.size)
    features.append(edge_density)

    aspect_ratio = float(width) / float(height)
    pixel_area = float(width * height)
    features.append(aspect_ratio)
    features.append(np.log1p(pixel_area) / 20.0)

    return [float(v) for v in features]
