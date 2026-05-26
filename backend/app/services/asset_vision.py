import json
import tempfile
from pathlib import Path
from typing import Any

import httpx
from PIL import Image

from app.core.config import settings


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


def analyze_image_asset(image_path: Path) -> dict[str, Any]:
    text_blocks, ocr_status, ocr_error = extract_ocr_text(image_path)
    visual_regions = _extract_visual_regions(image_path)
    return {
        "text_blocks": text_blocks,
        "visual_regions": visual_regions,
        "ocr_status": ocr_status,
        "ocr_error": ocr_error,
    }


def vision_data_to_json(vision_data: dict[str, Any]) -> str:
    return json.dumps(vision_data, ensure_ascii=False)
