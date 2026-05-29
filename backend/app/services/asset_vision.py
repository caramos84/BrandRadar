import json
import math
import tempfile
from pathlib import Path
from typing import Any

import httpx
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

from app.core.config import settings
from app.services.layout_analysis import compute_layout_analysis
from app.services.linguistic_stress import compute_linguistic_stress


def create_ocr_optimized_image(image_path: Path) -> Path | None:
    """Create a temporary OCR-optimized image to avoid 413 Payload Too Large.

    Resizes to max 1600x1600, converts to RGB, compresses to JPEG quality 80.
    Returns temp file path or None if optimization fails.
    """
    try:
        with Image.open(image_path) as img:
            if img.mode != "RGB":
                img = img.convert("RGB")
            img.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
            temp_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
            temp_path = Path(temp_file.name)
            temp_file.close()
            img.save(temp_path, format="JPEG", quality=80, optimize=True)
            return temp_path
    except Exception:
        return None


def run_tesseract_ocr(image_path: Path) -> tuple[list[dict[str, Any]], str, str | None]:
    try:
        import pytesseract
    except Exception:
        return [], "unavailable", "pytesseract module unavailable"

    try:
        with Image.open(image_path) as image:
            ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    except pytesseract.pytesseract.TesseractNotFoundError:
        return [], "unavailable", "pytesseract binary not available"
    except Exception as exc:
        return [], "failed", str(exc)[:240]

    text_blocks: list[dict[str, Any]] = []
    for idx, text in enumerate(ocr_data.get("text", [])):
        clean_text = (text or "").strip()
        if not clean_text:
            continue

        x = int(ocr_data.get("left", [0])[idx])
        y = int(ocr_data.get("top", [0])[idx])
        w = int(ocr_data.get("width", [0])[idx])
        h = int(ocr_data.get("height", [0])[idx])
        conf_raw = ocr_data.get("conf", [None])[idx]

        confidence: float | None
        try:
            conf_value = float(conf_raw)
            confidence = None if conf_value < 0 else conf_value
        except Exception:
            confidence = None

        text_blocks.append(
            {
                "text": clean_text,
                "bbox": [x, y, w, h],
                "confidence": confidence,
            }
        )

    if text_blocks:
        return text_blocks, "completed", None

    return [], "completed_empty", None


def run_ocr_space(image_path: Path) -> tuple[list[dict[str, Any]], str, str | None]:
    if not settings.ocr_space_api_key:
        return [], "unavailable", "ocr.space api key not configured"

    ocr_image_path = create_ocr_optimized_image(image_path)
    if ocr_image_path is None:
        ocr_image_path = image_path

    try:
        with ocr_image_path.open("rb") as image_file:
            files = {
                "file": (ocr_image_path.name, image_file, "application/octet-stream"),
            }
            response = httpx.post(
                settings.ocr_space_endpoint,
                data={
                    "apikey": settings.ocr_space_api_key,
                    "language": "spa",
                    "isOverlayRequired": "false",
                },
                files=files,
                timeout=30.0,
            )
        response.raise_for_status()
        result = response.json()
    except Exception as exc:
        return [], "failed", f"ocr.space request failed: {str(exc)[:220]}"
    finally:
        if ocr_image_path != image_path:
            try:
                ocr_image_path.unlink()
            except Exception:
                pass

    if result.get("IsErroredOnProcessing"):
        error_messages = result.get("ErrorMessage")
        if isinstance(error_messages, list):
            error_text = "; ".join(str(message) for message in error_messages if message)
        else:
            error_text = str(error_messages or "OCR.space error")
        return [], "failed", f"ocr.space processing failed: {error_text}"

    parsed_results = result.get("ParsedResults")
    if not parsed_results or not isinstance(parsed_results, list):
        return [], "failed", "ocr.space returned invalid ParsedResults"

    parsed_text = (parsed_results[0].get("ParsedText") or "").strip()
    if not parsed_text:
        return [], "completed_empty", None

    return [
        {
            "text": parsed_text,
            "bbox": [0, 0, 0, 0],
            "confidence": None,
        }
    ], "completed", None


def extract_ocr_text(image_path: Path) -> tuple[list[dict[str, Any]], str, str | None]:
    provider = (settings.ocr_provider or "auto").strip().lower()
    if provider == "tesseract":
        return run_tesseract_ocr(image_path)
    if provider == "ocr_space":
        return run_ocr_space(image_path)

    text_blocks, ocr_status, ocr_error = run_tesseract_ocr(image_path)
    if ocr_status in {"completed", "completed_empty"}:
        return text_blocks, ocr_status, ocr_error
    if ocr_status == "unavailable" and settings.ocr_space_api_key:
        return run_ocr_space(image_path)

    return text_blocks, ocr_status, ocr_error


def _extract_visual_regions(image_path: Path) -> list[dict[str, Any]]:
    try:
        import cv2
    except Exception:
        return []

    image = cv2.imread(str(image_path))
    if image is None:
        return []

    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, threshold1=40, threshold2=140)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        merged = cv2.dilate(edges, kernel, iterations=1)
        contours, _ = cv2.findContours(merged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    except Exception:
        return []

    image_area = image.shape[0] * image.shape[1]
    min_area = max(400, int(image_area * 0.0015))

    regions: list[dict[str, Any]] = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h
        if area < min_area:
            continue

        confidence = min(1.0, area / max(1, image_area))
        regions.append(
            {
                "label": "visual_region",
                "bbox": [int(x), int(y), int(w), int(h)],
                "confidence": round(confidence, 4),
            }
        )

    regions.sort(key=lambda region: region["bbox"][2] * region["bbox"][3], reverse=True)
    return regions[:20]


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def normalize_array(arr: np.ndarray) -> np.ndarray:
    arr = np.asarray(arr, dtype=float)
    min_v = np.nanmin(arr)
    max_v = np.nanmax(arr)
    if max_v - min_v < 1e-9:
        return np.zeros_like(arr)
    return (arr - min_v) / (max_v - min_v)


def gaussian_blur_grid(grid: np.ndarray, passes: int = 2) -> np.ndarray:
    grid = grid.astype(float)
    for _ in range(passes):
        padded = np.pad(grid, 1, mode="edge")
        out = np.zeros_like(grid)
        for y in range(grid.shape[0]):
            for x in range(grid.shape[1]):
                region = padded[y : y + 3, x : x + 3]
                kernel = np.array([[1, 2, 1], [2, 4, 2], [1, 2, 1]], dtype=float)
                out[y, x] = np.sum(region * kernel) / kernel.sum()
        grid = out
    return grid


def compute_attention_grid(image: Image.Image, grid_w: int = 12, grid_h: int = 12) -> np.ndarray:
    width, height = image.size
    gray = np.asarray(image.convert("L"), dtype=float) / 255.0
    hsv = image.convert("HSV")
    hsv_arr = np.asarray(hsv).astype(float)
    sat_arr = hsv_arr[:, :, 1] / 255.0

    dy = np.abs(np.diff(gray, axis=0, prepend=gray[:1, :]))
    dx = np.abs(np.diff(gray, axis=1, prepend=gray[:, :1]))
    edge_map = normalize_array(np.hypot(dx, dy))

    activity = np.zeros((grid_h, grid_w), dtype=float)
    for gy in range(grid_h):
        for gx in range(grid_w):
            x0 = int(gx * width / grid_w)
            x1 = int((gx + 1) * width / grid_w)
            y0 = int(gy * height / grid_h)
            y1 = int((gy + 1) * height / grid_h)
            patch = gray[y0:y1, x0:x1]
            if patch.size == 0:
                continue
            contrast = float(patch.max() - patch.min())
            std = float(np.std(patch))
            edge_density = float(np.mean(edge_map[y0:y1, x0:x1] > 0.12))
            saturation_variation = float(np.std(sat_arr[y0:y1, x0:x1]))
            cx = (gx + 0.5) / grid_w
            cy = (gy + 0.5) / grid_h
            distance = math.hypot(cx - 0.5, cy - 0.5)
            centrality_bias = 1.0 - clamp01(distance / 0.75)
            activity[gy, gx] = clamp01(
                contrast * 0.55
                + std * 0.15
                + edge_density * 0.15
                + saturation_variation * 0.10
                + centrality_bias * 0.05
            )

    blurred = gaussian_blur_grid(activity, passes=3)
    return normalize_array(blurred)


def attention_value_to_rgba(value: float) -> tuple[int, int, int, int]:
    v = clamp01(value)
    stops = [
        (0.0, (28, 107, 255)),
        (0.25, (0, 211, 255)),
        (0.5, (80, 224, 100)),
        (0.75, (255, 219, 76)),
        (1.0, (255, 69, 0)),
    ]
    lower_val, lower_color = stops[0]
    upper_val, upper_color = stops[-1]
    for i in range(len(stops) - 1):
        if v <= stops[i + 1][0]:
            lower_val, lower_color = stops[i]
            upper_val, upper_color = stops[i + 1]
            break
    ratio = (v - lower_val) / max(1e-9, upper_val - lower_val)
    r = round(lower_color[0] + (upper_color[0] - lower_color[0]) * ratio)
    g = round(lower_color[1] + (upper_color[1] - lower_color[1]) * ratio)
    b = round(lower_color[2] + (upper_color[2] - lower_color[2]) * ratio)
    alpha = int(clamp01(v) * 200 + 40)
    return (r, g, b, min(alpha, 230))


def build_attention_overlay(attention_grid: np.ndarray, target_size: tuple[int, int]) -> Image.Image:
    grid_h, grid_w = attention_grid.shape
    overlay_small = Image.new("RGBA", (grid_w, grid_h))
    for gy in range(grid_h):
        for gx in range(grid_w):
            overlay_small.putpixel((gx, gy), attention_value_to_rgba(float(attention_grid[gy, gx])))
    overlay = overlay_small.resize(target_size, resample=Image.BILINEAR)
    overlay = overlay.filter(ImageFilter.GaussianBlur(radius=12))
    return overlay


def compute_attention_metrics(attention_grid: np.ndarray) -> dict[str, float]:
    flat = attention_grid.flatten()
    if flat.size == 0:
        return {
            "focus_clarity": 0.0,
            "attention_dispersion": 0.0,
            "visual_noise": 0.0,
            "primary_attention_score": 0.0,
            "top3_attention_mean": 0.0,
        }
    normalized = flat / (flat.sum() + 1e-9)
    entropy = -float(np.sum(normalized * np.log(normalized + 1e-9)))
    max_entropy = math.log(len(flat)) if len(flat) > 1 else 1.0
    dispersion = clamp01(entropy / max_entropy) if max_entropy > 0 else 0.0
    sorted_values = np.sort(flat)[::-1]
    top1 = float(sorted_values[0])
    top3_mean = float(sorted_values[:3].mean())
    overall_mean = float(flat.mean())
    focus_clarity = clamp01(0.5 * top1 + 0.3 * top3_mean + 0.2 * (1.0 - dispersion))
    visual_noise = clamp01(dispersion * 0.6 + overall_mean * 0.4)
    return {
        "focus_clarity": focus_clarity,
        "attention_dispersion": dispersion,
        "visual_noise": visual_noise,
        "primary_attention_score": top1,
        "top3_attention_mean": top3_mean,
    }


def generate_attention_reading(metrics: dict[str, float]) -> str:
    if not metrics:
        return ""
    focus = metrics.get("focus_clarity", 0.0)
    dispersion = metrics.get("attention_dispersion", 0.0)
    if focus >= 0.70:
        focus_desc = "clear primary focus"
    elif focus >= 0.45:
        focus_desc = "moderate attention focus"
    else:
        focus_desc = "diffuse attention distribution"
    if dispersion >= 0.70:
        dispersion_desc = "attention is widely dispersed"
    elif dispersion >= 0.45:
        dispersion_desc = "attention is moderately distributed"
    else:
        dispersion_desc = "attention is concentrated in a few strong areas"
    return f"The asset shows {focus_desc}, and {dispersion_desc}."


def compute_attention_heatmap(image_path: Path) -> dict[str, Any]:
    try:
        with Image.open(image_path) as img:
            if img.mode != "RGB":
                img = img.convert("RGB")
            attention_grid = compute_attention_grid(img, grid_w=12, grid_h=12)
            attention_metrics = compute_attention_metrics(attention_grid)
            attention_reading = generate_attention_reading(attention_metrics)

            overlay = build_attention_overlay(attention_grid, img.size)
            base_rgba = img.convert("RGBA")
            composite = Image.alpha_composite(base_rgba, overlay)

            heatmap_filename = f"{image_path.stem}_attention_heatmap.png"
            heatmap_output = image_path.parent / heatmap_filename
            composite.save(heatmap_output, format="PNG", optimize=True)
            attention_heatmap_path = f"/storage/uploads/{heatmap_filename}"

            return {
                "attention_grid": attention_grid.tolist(),
                "attention_metrics": attention_metrics,
                "attention_reading": attention_reading,
                "attention_heatmap_path": attention_heatmap_path,
            }
    except Exception:
        return {
            "attention_grid": [],
            "attention_metrics": {},
            "attention_reading": "",
            "attention_heatmap_path": None,
        }


def analyze_image_asset(image_path: Path) -> dict[str, Any]:
    text_blocks, ocr_status, ocr_error = extract_ocr_text(image_path)
    visual_regions = _extract_visual_regions(image_path)
    heatmap_data = compute_attention_heatmap(image_path)
    layout_analysis = compute_layout_analysis(
        image_path=image_path,
        text_blocks=text_blocks,
        visual_regions=visual_regions,
        attention_grid=heatmap_data.get("attention_grid"),
        attention_metrics=heatmap_data.get("attention_metrics"),
    )
    linguistic_stress = compute_linguistic_stress(
        text_blocks=text_blocks,
        layout_analysis=layout_analysis,
        baseline_language="en",
    )
    return {
        "text_blocks": text_blocks,
        "visual_regions": visual_regions,
        "ocr_status": ocr_status,
        "ocr_error": ocr_error,
        "layout_analysis": layout_analysis,
        "linguistic_stress": linguistic_stress,
        **heatmap_data,
    }


def vision_data_to_json(vision_data: dict[str, Any]) -> str:
    return json.dumps(vision_data, ensure_ascii=False)
