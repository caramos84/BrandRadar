import json
from pathlib import Path
from typing import Any

from PIL import Image


def _extract_text_blocks(image_path: Path) -> list[dict[str, Any]]:
    try:
        import pytesseract
    except Exception:
        return []

    try:
        with Image.open(image_path) as image:
            ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    except Exception:
        return []

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

    return text_blocks


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


def analyze_image_asset(image_path: Path) -> dict[str, Any]:
    text_blocks = _extract_text_blocks(image_path)
    visual_regions = _extract_visual_regions(image_path)
    return {
        "text_blocks": text_blocks,
        "visual_regions": visual_regions,
    }


def vision_data_to_json(vision_data: dict[str, Any]) -> str:
    return json.dumps(vision_data, ensure_ascii=False)
