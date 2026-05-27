import json
from pathlib import Path
from typing import Any

from PIL import Image


def _extract_text_blocks(image_path: Path) -> tuple[list[dict[str, Any]], str, str | None]:
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


def _generate_attention_artifacts(image_path: Path) -> dict[str, Any]:
    """Generate attention grid + heatmap image. Best effort only."""
    try:
        import cv2
        import numpy as np
    except Exception:
        return {}

    image = cv2.imread(str(image_path))
    if image is None:
        return {}

    try:
        h, w = image.shape[:2]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)

        lap = cv2.Laplacian(gray, cv2.CV_32F)
        lap = np.abs(lap)
        edges = cv2.Canny(gray, 60, 160).astype(np.float32) / 255.0

        saliency = (lap / (lap.max() + 1e-6)) * 0.7 + edges * 0.3
        saliency = cv2.GaussianBlur(saliency, (0, 0), 2.0)

        grid_small = cv2.resize(saliency, (12, 12), interpolation=cv2.INTER_AREA)
        grid_small = grid_small - grid_small.min()
        grid_small = grid_small / (grid_small.max() + 1e-6)

        grid_list = [[float(round(v, 4)) for v in row] for row in grid_small.tolist()]

        upscaled = cv2.resize(grid_small.astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC)
        upscaled = cv2.GaussianBlur(upscaled, (0, 0), 8.0)
        upscaled = np.clip(upscaled, 0.0, 1.0)

        heat_u8 = np.uint8(upscaled * 255)
        heat_color = cv2.applyColorMap(heat_u8, cv2.COLORMAP_JET)
        composed = cv2.addWeighted(image, 0.48, heat_color, 0.52, 0)

        out_name = f"{image_path.stem}_attention_heatmap.png"
        out_path = image_path.with_name(out_name)
        cv2.imwrite(str(out_path), composed)

        cell_h = h / 12.0
        cell_w = w / 12.0
        flat = [(v, r, c) for r, row in enumerate(grid_small.tolist()) for c, v in enumerate(row)]
        flat.sort(key=lambda item: item[0], reverse=True)
        zones = []
        for idx, (value, r, c) in enumerate(flat[:3]):
            zones.append({
                "rank": idx + 1,
                "score": float(round(value, 4)),
                "bbox": [int(c * cell_w), int(r * cell_h), int(cell_w), int(cell_h)],
            })

        metrics = {
            "max_attention": float(round(float(grid_small.max()), 4)),
            "mean_attention": float(round(float(grid_small.mean()), 4)),
            "dispersion": float(round(float(grid_small.std()), 4)),
        }

        reading = "Focus appears concentrated" if metrics["dispersion"] > 0.23 else "Focus appears distributed"

        return {
            "attention_grid": grid_list,
            "attention_zones": zones,
            "attention_metrics": metrics,
            "attention_reading": reading,
            "attention_heatmap_path": f"/storage/uploads/{out_name}",
        }
    except Exception:
        return {}


def analyze_image_asset(image_path: Path) -> dict[str, Any]:
    text_blocks, ocr_status, ocr_error = _extract_text_blocks(image_path)
    visual_regions = _extract_visual_regions(image_path)
    attention_artifacts = _generate_attention_artifacts(image_path)
    return {
        "text_blocks": text_blocks,
        "visual_regions": visual_regions,
        "ocr_status": ocr_status,
        "ocr_error": ocr_error,
        **attention_artifacts,
    }


def vision_data_to_json(vision_data: dict[str, Any]) -> str:
    return json.dumps(vision_data, ensure_ascii=False)
