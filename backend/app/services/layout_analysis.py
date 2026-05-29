from __future__ import annotations

import math
import re
import struct
import unicodedata
from pathlib import Path
from typing import Any

BLOCK_TYPES = {
    "Hero / Main Visual",
    "Secondary Visual",
    "Logo / Brand",
    "Headline",
    "Price / Offer",
    "CTA",
    "Product / Packshot",
    "Legal / Footer",
    "Background / Texture",
    "Unknown Structural Block",
}
SOURCES = {"visual", "ocr", "combined"}

PRICE_TERMS = {
    "precio", "price", "oferta", "ofertas", "descuento", "descuentos", "dcto", "dto", "cuota", "cuotas",
    "sale", "black friday", "black days", "promo", "promocion", "rebaja", "ahorro", "gratis", "bono", "bonos",
}
CTA_TERMS = {"compra", "comprar", "conoce", "entra", "aprovecha", "recibe", "usa", "usando", "lleva", "estrena"}
LEGAL_TERMS = {"legal", "terminos", "condiciones", "aplica", "vigencia", "valido", "valida", "restricciones"}
BRAND_TERMS = {"logo", "marca", "marcas", "brand", "addi", "samsung", "decathlon"}
PRODUCT_TERMS = {"producto", "pack", "packshot", "phone", "shoe", "botella", "plan", "tarjeta"}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _normalize_text(raw: str) -> str:
    normalized = unicodedata.normalize("NFKD", raw.lower())
    without_accents = "".join(char for char in normalized if not unicodedata.combining(char))
    spaced = re.sub(r"[_\-.]", " ", without_accents)
    spaced = re.sub(r"[^a-z0-9%+$\s]", " ", spaced)
    return re.sub(r"\s+", " ", spaced).strip()


def _count_terms(text: str, terms: set[str]) -> int:
    count = 0
    for term in terms:
        normalized_term = _normalize_text(term)
        if " " in normalized_term:
            count += text.count(normalized_term)
        else:
            count += len(re.findall(rf"\b{re.escape(normalized_term)}\b", text))
    return count


def _read_image_size(image_path: Path) -> tuple[int, int]:
    try:
        from PIL import Image

        with Image.open(image_path) as img:
            return int(img.width), int(img.height)
    except Exception:
        pass

    try:
        with image_path.open("rb") as handle:
            header = handle.read(32)
        if header.startswith(b"\x89PNG\r\n\x1a\n") and len(header) >= 24:
            width, height = struct.unpack(">II", header[16:24])
            return int(width), int(height)
    except Exception:
        pass
    return 0, 0


def _bbox(raw: Any) -> tuple[float, float, float, float] | None:
    if not isinstance(raw, (list, tuple)) or len(raw) < 4:
        return None
    try:
        x, y, w, h = float(raw[0]), float(raw[1]), float(raw[2]), float(raw[3])
    except (TypeError, ValueError):
        return None
    if w <= 0 or h <= 0:
        return None
    return x, y, w, h


def _clamp_box(box: tuple[float, float, float, float], width: int, height: int) -> tuple[int, int, int, int] | None:
    if width <= 0 or height <= 0:
        return None
    x, y, w, h = box
    x1 = int(round(_clamp(x, 0, width)))
    y1 = int(round(_clamp(y, 0, height)))
    x2 = int(round(_clamp(x + w, 0, width)))
    y2 = int(round(_clamp(y + h, 0, height)))
    if x2 <= x1 or y2 <= y1:
        return None
    return x1, y1, x2 - x1, y2 - y1


def _area(box: dict[str, Any]) -> int:
    return int(box["width_px"]) * int(box["height_px"])


def _iou(a: dict[str, Any], b: dict[str, Any]) -> float:
    ax1, ay1 = a["x_px"], a["y_px"]
    ax2, ay2 = ax1 + a["width_px"], ay1 + a["height_px"]
    bx1, by1 = b["x_px"], b["y_px"]
    bx2, by2 = bx1 + b["width_px"], by1 + b["height_px"]
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    inter = (ix2 - ix1) * (iy2 - iy1)
    union = _area(a) + _area(b) - inter
    return inter / max(1, union)


def _center_inside(inner: dict[str, Any], outer: dict[str, Any]) -> bool:
    cx = inner["x_px"] + inner["width_px"] / 2
    cy = inner["y_px"] + inner["height_px"] / 2
    return outer["x_px"] <= cx <= outer["x_px"] + outer["width_px"] and outer["y_px"] <= cy <= outer["y_px"] + outer["height_px"]


def _make_candidate(
    box: tuple[int, int, int, int],
    image_width: int,
    image_height: int,
    confidence: float,
    source: str,
    text: str = "",
) -> dict[str, Any]:
    x, y, w, h = box
    canvas_area = max(1, image_width * image_height)
    return {
        "x_px": x,
        "y_px": y,
        "width_px": w,
        "height_px": h,
        "x": round(x / image_width, 4) if image_width else 0.0,
        "y": round(y / image_height, 4) if image_height else 0.0,
        "width": round(w / image_width, 4) if image_width else 0.0,
        "height": round(h / image_height, 4) if image_height else 0.0,
        "area_pct": round((w * h / canvas_area) * 100, 2),
        "confidence": round(_clamp(confidence, 0.0, 1.0), 4),
        "source": source if source in SOURCES else "visual",
        "text": text,
    }


def _visual_candidates(visual_regions: list[dict[str, Any]], image_width: int, image_height: int) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    min_area = max(24, image_width * image_height * 0.0025)
    for region in visual_regions if isinstance(visual_regions, list) else []:
        if not isinstance(region, dict):
            continue
        raw_box = _bbox(region.get("bbox"))
        if raw_box is None:
            continue
        box = _clamp_box(raw_box, image_width, image_height)
        if box is None or box[2] * box[3] < min_area:
            continue
        confidence = region.get("confidence", 0.55)
        try:
            confidence_value = float(confidence)
        except (TypeError, ValueError):
            confidence_value = 0.55
        candidates.append(_make_candidate(box, image_width, image_height, confidence_value, "visual"))
    return candidates


def _ocr_candidates(text_blocks: list[dict[str, Any]], image_width: int, image_height: int) -> tuple[list[dict[str, Any]], str]:
    candidates: list[dict[str, Any]] = []
    all_text: list[str] = []
    min_area = max(10, image_width * image_height * 0.0002)
    for block in text_blocks if isinstance(text_blocks, list) else []:
        if not isinstance(block, dict):
            continue
        text = str(block.get("text", "")).strip()
        if text:
            all_text.append(text)
        raw_box = _bbox(block.get("bbox"))
        if raw_box is None:
            continue
        box = _clamp_box(raw_box, image_width, image_height)
        if box is None or box[2] * box[3] < min_area:
            continue
        confidence = block.get("confidence", 0.65)
        try:
            confidence_value = float(confidence)
            if confidence_value > 1:
                confidence_value = confidence_value / 100
        except (TypeError, ValueError):
            confidence_value = 0.65
        candidates.append(_make_candidate(box, image_width, image_height, confidence_value, "ocr", text=text))
    return candidates, " ".join(all_text)


def _attach_text_to_visuals(visuals: list[dict[str, Any]], ocr_blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    used_ocr: set[int] = set()
    for visual in visuals:
        texts: list[str] = []
        confidences = [visual["confidence"]]
        for index, ocr in enumerate(ocr_blocks):
            if _iou(visual, ocr) >= 0.08 or _center_inside(ocr, visual):
                texts.append(ocr.get("text", ""))
                confidences.append(ocr["confidence"])
                used_ocr.add(index)
        if texts:
            visual["text"] = " ".join(text for text in texts if text)
            visual["source"] = "combined"
            visual["confidence"] = round(min(1.0, sum(confidences) / len(confidences) + 0.08), 4)
    return visuals + [ocr for index, ocr in enumerate(ocr_blocks) if index not in used_ocr]


def _suppress_duplicates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(candidates, key=lambda item: (_area(item), item["confidence"]), reverse=True)
    kept: list[dict[str, Any]] = []
    for candidate in ordered:
        duplicate = False
        for existing in kept:
            overlap = _iou(candidate, existing)
            smaller_area = max(1, min(_area(candidate), _area(existing)))
            ax1, ay1 = candidate["x_px"], candidate["y_px"]
            ax2, ay2 = ax1 + candidate["width_px"], ay1 + candidate["height_px"]
            bx1, by1 = existing["x_px"], existing["y_px"]
            bx2, by2 = bx1 + existing["width_px"], by1 + existing["height_px"]
            ix1, iy1 = max(ax1, bx1), max(ay1, by1)
            ix2, iy2 = min(ax2, bx2), min(ay2, by2)
            inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
            if overlap >= 0.72 or inter / smaller_area >= 0.88:
                duplicate = True
                break
        if not duplicate:
            kept.append(candidate)
    return kept


def _text_scores(text: str) -> dict[str, int]:
    normalized = _normalize_text(text)
    price_hits = _count_terms(normalized, PRICE_TERMS) + len(re.findall(r"\$\s*[\d.,]+|\d+\s*%|\b\d+\s*(cuotas?|dto|dcto)\b", normalized))
    return {
        "price": price_hits,
        "cta": _count_terms(normalized, CTA_TERMS),
        "legal": _count_terms(normalized, LEGAL_TERMS),
        "brand": _count_terms(normalized, BRAND_TERMS),
        "product": _count_terms(normalized, PRODUCT_TERMS),
        "words": len(re.findall(r"\b\w+\b", normalized)),
    }


def _classify(candidate: dict[str, Any], index: int, largest_area: int, image_width: int, image_height: int) -> str:
    text = candidate.get("text", "")
    scores = _text_scores(text)
    x, y, w, h = candidate["x"], candidate["y"], candidate["width"], candidate["height"]
    area_pct = candidate["area_pct"]
    center_x = x + w / 2
    center_y = y + h / 2

    if scores["price"] > 0:
        return "Price / Offer"
    if scores["cta"] > 0:
        return "CTA"
    if (y > 0.80 and (area_pct <= 12 or scores["legal"] > 0 or scores["words"] >= 6)) or scores["legal"] >= 2:
        return "Legal / Footer"
    if scores["brand"] > 0 and area_pct <= 18 and (x < 0.28 or x + w > 0.72 or y < 0.24 or y > 0.72):
        return "Logo / Brand"
    if candidate["source"] == "ocr" and y < 0.28 and w > 0.22 and scores["words"] >= 2:
        return "Headline"
    if index == 0 and (_area(candidate) >= largest_area * 0.72 or (area_pct >= 16 and 0.25 <= center_x <= 0.75 and 0.20 <= center_y <= 0.78)):
        return "Hero / Main Visual"
    if scores["product"] > 0 or (area_pct >= 8 and 0.25 <= center_y <= 0.82 and candidate["source"] in {"visual", "combined"}):
        return "Product / Packshot"
    if candidate["source"] == "visual" and area_pct >= 65:
        return "Background / Texture"
    if candidate["source"] in {"visual", "combined"}:
        return "Secondary Visual"
    return "Unknown Structural Block"


def _summarize(blocks: list[dict[str, Any]], attention_metrics: dict[str, Any]) -> dict[str, Any]:
    block_count = len(blocks)
    if not blocks:
        return {
            "framework": "General Asset",
            "composition": "Full-bleed",
            "dominant_element": "Unknown Structural Block",
            "layout_complexity": "Low",
            "focus_behavior": "Undetected",
            "commercial_structure": "Soft / Atmospheric",
            "hierarchy": [],
            "block_count": 0,
        }

    hierarchy_blocks = sorted(blocks, key=lambda block: (block["area_pct"], block["confidence"]), reverse=True)
    hierarchy = [block["type"] for block in hierarchy_blocks[:5]]
    types = {block["type"] for block in blocks}
    dominant = hierarchy_blocks[0]

    centers_x = [block["x"] + block["width"] / 2 for block in blocks]
    centers_y = [block["y"] + block["height"] / 2 for block in blocks]
    x_spread = max(centers_x) - min(centers_x) if len(centers_x) > 1 else 0
    y_spread = max(centers_y) - min(centers_y) if len(centers_y) > 1 else 0
    if dominant["area_pct"] > 58:
        composition = "Full-bleed"
    elif block_count >= 6 and x_spread > 0.45 and y_spread > 0.35:
        composition = "Grid / Modular"
    elif block_count >= 4 and x_spread > 0.55:
        composition = "Multi-panel"
    elif x_spread > y_spread + 0.15:
        composition = "Split"
    elif abs((dominant["x"] + dominant["width"] / 2) - 0.5) <= 0.12:
        composition = "Centered"
    else:
        composition = "Asymmetric"

    if block_count <= 3:
        complexity = "Low"
    elif block_count <= 7:
        complexity = "Medium"
    else:
        complexity = "High"

    focus_clarity = 0.0
    try:
        focus_clarity = float((attention_metrics or {}).get("focus_clarity", 0.0))
    except (TypeError, ValueError):
        focus_clarity = 0.0
    second_area = hierarchy_blocks[1]["area_pct"] if len(hierarchy_blocks) > 1 else 0
    dominance_gap = dominant["area_pct"] - second_area
    if focus_clarity >= 0.65 or dominance_gap >= 20:
        focus_behavior = "Focused"
    elif focus_clarity >= 0.35 or dominance_gap >= 8:
        focus_behavior = "Moderately Focused"
    else:
        focus_behavior = "Distributed"

    has_price = "Price / Offer" in types
    has_cta = "CTA" in types
    has_hero = "Hero / Main Visual" in types
    has_product = "Product / Packshot" in types
    has_logo = "Logo / Brand" in types
    if has_price and has_cta:
        commercial = "Conversion Led"
        framework = "Retail Promo"
    elif has_price or has_cta:
        commercial = "Moderate Conversion"
        framework = "Retail Promo"
    elif block_count >= 7:
        commercial = "Information Led"
        framework = "Dense Information Layout"
    elif has_product or has_hero:
        commercial = "Product Led" if has_product else "Soft / Atmospheric"
        framework = "Product Showcase"
    elif has_logo and block_count <= 3:
        commercial = "Soft / Atmospheric"
        framework = "Brand / Lifestyle"
    else:
        commercial = "Soft / Atmospheric"
        framework = "General Asset"

    return {
        "framework": framework,
        "composition": composition,
        "dominant_element": dominant["type"],
        "layout_complexity": complexity,
        "focus_behavior": focus_behavior,
        "commercial_structure": commercial,
        "hierarchy": hierarchy,
        "block_count": block_count,
    }


def _reading(summary: dict[str, Any]) -> str:
    hierarchy = summary.get("hierarchy") or []
    hierarchy_text = ", ".join(hierarchy) if hierarchy else "no stable structural hierarchy"
    return (
        f"The asset uses a {summary['framework']} framework with a {summary['composition']} composition. "
        f"The dominant element is {summary['dominant_element']}. "
        f"The visual hierarchy follows: {hierarchy_text}. "
        f"Layout complexity is {summary['layout_complexity']}, with {summary['focus_behavior']} attention behavior. "
        f"The commercial structure is {summary['commercial_structure']}."
    )


def _artifact_url(path: Path) -> str:
    return f"/storage/uploads/{path.name}"


def _draw_artifacts(image_path: Path, blocks: list[dict[str, Any]], image_width: int, image_height: int) -> dict[str, str | None]:
    overlay_path: str | None = None
    wireframe_path: str | None = None
    try:
        from PIL import Image, ImageDraw

        colors = {
            "Hero / Main Visual": "cyan",
            "Secondary Visual": "orange",
            "Logo / Brand": "lime",
            "Headline": "yellow",
            "Price / Offer": "magenta",
            "CTA": "red",
            "Product / Packshot": "green",
            "Legal / Footer": "gray",
            "Background / Texture": "blue",
            "Unknown Structural Block": "white",
        }
        with Image.open(image_path) as original:
            overlay = original.convert("RGB")
        overlay_draw = ImageDraw.Draw(overlay)
        for block in blocks:
            color = colors.get(block["type"], "white")
            x1, y1 = block["x_px"], block["y_px"]
            x2, y2 = x1 + block["width_px"], y1 + block["height_px"]
            label = f"{block['id']} {block['type']}"
            overlay_draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
            overlay_draw.text((x1 + 4, y1 + 4), label, fill=color)
        overlay_file = image_path.with_name(f"{image_path.stem}_layout_overlay.png")
        overlay.save(overlay_file, format="PNG", optimize=True)
        overlay_path = _artifact_url(overlay_file)

        wireframe = Image.new("RGB", (max(1, image_width), max(1, image_height)), (24, 24, 28))
        wire_draw = ImageDraw.Draw(wireframe)
        for block in blocks:
            x1, y1 = block["x_px"], block["y_px"]
            x2, y2 = x1 + block["width_px"], y1 + block["height_px"]
            label = f"{block['id']} {block['type']}"
            wire_draw.rectangle([x1, y1, x2, y2], outline="white", width=3)
            wire_draw.text((x1 + 4, y1 + 4), label, fill="white")
        wireframe_file = image_path.with_name(f"{image_path.stem}_layout_wireframe.png")
        wireframe.save(wireframe_file, format="PNG", optimize=True)
        wireframe_path = _artifact_url(wireframe_file)
    except Exception:
        overlay_path = None
        wireframe_path = None
    return {"layout_overlay_path": overlay_path, "layout_wireframe_path": wireframe_path}


def compute_layout_analysis(
    image_path: Path,
    text_blocks: list[dict[str, Any]],
    visual_regions: list[dict[str, Any]],
    attention_grid: list[list[float]] | None = None,
    attention_metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    image_width, image_height = _read_image_size(image_path)
    safe_text_blocks = text_blocks if isinstance(text_blocks, list) else []
    safe_visual_regions = visual_regions if isinstance(visual_regions, list) else []
    safe_attention_metrics = attention_metrics if isinstance(attention_metrics, dict) else {}

    visual_candidates = _visual_candidates(safe_visual_regions, image_width, image_height)
    ocr_candidates, global_text = _ocr_candidates(safe_text_blocks, image_width, image_height)
    candidates = _attach_text_to_visuals(visual_candidates, ocr_candidates)
    candidates = _suppress_duplicates(candidates)[:12]

    largest = max((_area(candidate) for candidate in candidates), default=0)
    blocks: list[dict[str, Any]] = []
    for index, candidate in enumerate(candidates):
        block_type = _classify(candidate, index, largest, image_width, image_height)
        if block_type not in BLOCK_TYPES:
            block_type = "Unknown Structural Block"
        block = {
            "id": f"layout-block-{len(blocks) + 1}",
            "type": block_type,
            "x": candidate["x"],
            "y": candidate["y"],
            "width": candidate["width"],
            "height": candidate["height"],
            "x_px": candidate["x_px"],
            "y_px": candidate["y_px"],
            "width_px": candidate["width_px"],
            "height_px": candidate["height_px"],
            "area_pct": candidate["area_pct"],
            "confidence": candidate["confidence"],
            "source": candidate["source"],
        }
        blocks.append(block)

    if not blocks and global_text:
        # Keep invalid OCR text as semantic context only; it must not create spatial blocks.
        pass

    blocks = sorted(blocks, key=lambda block: (block["area_pct"], block["confidence"]), reverse=True)
    summary = _summarize(blocks, safe_attention_metrics)
    artifacts = _draw_artifacts(image_path, blocks, image_width, image_height) if blocks else {
        "layout_overlay_path": None,
        "layout_wireframe_path": None,
    }
    return {
        "version": 1,
        "image": {"width_px": image_width, "height_px": image_height},
        "summary": summary,
        "blocks": blocks,
        "artifacts": artifacts,
        "reading": _reading(summary),
    }
