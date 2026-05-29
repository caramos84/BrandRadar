import math
import re
import unicodedata
from typing import Any

PROMO_TERMS = {
    "promo", "promocion", "oferta", "ofert", "ofer", "ofe", "descuento", "dcto", "dto", "ahorro", "ahorra",
    "rebaja", "sale", "off", "gratis", "free", "2x1", "3x2",
}
PRICE_TERMS = {"precio", "price", "desde", "solo", "antes", "ahora", "por", "$", "cop", "pesos"}
CTA_TERMS = {
    "compra", "comprar", "conoce", "descubre", "aprovecha", "participa", "reclama", "redime", "lleva", "pide",
    "shop", "buy", "get", "claim", "order", "learn more",
}
URGENCY_TERMS = {"hoy", "ya", "ultimo", "ultimos", "ahora", "tiempo limitado", "solo hoy", "por tiempo limitado"}
BRAND_TERMS = {"logo", "marca", "brand", "brandmark", "isotype", "wordmark"}


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _score(value: float) -> float:
    return round(_clamp01(value) * 100.0, 2)


def _metric01(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    if numeric > 1.0:
        numeric = numeric / 100.0
    return _clamp01(numeric)


def _normalize_text(raw_text: str) -> str:
    lower = raw_text.lower()
    normalized = unicodedata.normalize("NFKD", lower)
    without_accents = "".join(char for char in normalized if not unicodedata.combining(char))
    spaced = re.sub(r"[_\-\.]", " ", without_accents)
    return re.sub(r"\s+", " ", spaced).strip()


def _text_from_blocks(text_blocks: list[Any]) -> tuple[list[str], str, str]:
    values: list[str] = []
    raw_values: list[str] = []
    for block in text_blocks:
        if isinstance(block, dict):
            text = str(block.get("text", "")).strip()
        else:
            text = str(block or "").strip()
        if not text:
            continue
        values.append(_normalize_text(text))
        raw_values.append(text)
    normalized = " ".join(values).strip()
    raw = " ".join(raw_values).strip()
    return values, normalized, raw


def _count_terms(text: str, terms: set[str]) -> int:
    count = 0
    for term in terms:
        if " " in term:
            count += text.count(term)
        else:
            count += len(re.findall(rf"\b{re.escape(term)}\b", text))
    return count


def _count_price_patterns(text: str) -> int:
    return len(re.findall(r"\$\s*[\d.,]+|[\d]+\s*%|\d+\s*\$", text, re.IGNORECASE))


def _bbox_values(item: Any) -> tuple[float, float, float, float] | None:
    if not isinstance(item, dict):
        return None
    bbox = item.get("bbox")
    if not isinstance(bbox, list | tuple) or len(bbox) < 4:
        return None
    try:
        x, y, w, h = (float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]))
    except (TypeError, ValueError):
        return None
    if w <= 0 or h <= 0:
        return None
    return x, y, w, h


def _canvas_area(text_blocks: list[Any], visual_regions: list[Any], attention_grid: list[Any]) -> float:
    max_x = 0.0
    max_y = 0.0
    for item in [*text_blocks, *visual_regions]:
        bbox = _bbox_values(item)
        if bbox is None:
            continue
        x, y, w, h = bbox
        max_x = max(max_x, x + w)
        max_y = max(max_y, y + h)
    if max_x > 0 and max_y > 0:
        return max(1.0, max_x * max_y)
    if attention_grid and isinstance(attention_grid, list):
        rows = len(attention_grid)
        cols = len(attention_grid[0]) if rows and isinstance(attention_grid[0], list) else 0
        if rows and cols:
            return float(rows * cols)
    return 1.0


def _text_density(text_blocks: list[Any], visual_regions: list[Any], attention_grid: list[Any]) -> float:
    text_area = 0.0
    boxed_count = 0
    for block in text_blocks:
        bbox = _bbox_values(block)
        if bbox is None:
            continue
        _, _, w, h = bbox
        text_area += w * h
        boxed_count += 1
    if text_area > 0:
        return _clamp01(text_area / _canvas_area(text_blocks, visual_regions, attention_grid))
    return _clamp01(len(text_blocks) / 18.0)


def _region_dispersion(visual_regions: list[Any], attention_grid: list[Any]) -> float:
    centroids: list[tuple[float, float, float]] = []
    for region in visual_regions:
        bbox = _bbox_values(region)
        if bbox is None:
            continue
        x, y, w, h = bbox
        centroids.append((x + w / 2.0, y + h / 2.0, max(1.0, w * h)))
    if len(centroids) < 2:
        return _grid_dispersion(attention_grid)
    max_x = max(cx for cx, _, _ in centroids)
    max_y = max(cy for _, cy, _ in centroids)
    diagonal = max(1.0, math.hypot(max_x, max_y))
    distances: list[float] = []
    for index, (cx, cy, _) in enumerate(centroids):
        for other_cx, other_cy, _ in centroids[index + 1:]:
            distances.append(math.hypot(cx - other_cx, cy - other_cy))
    return _clamp01((sum(distances) / len(distances)) / (diagonal * 0.6)) if distances else 0.0


def _grid_dispersion(attention_grid: list[Any]) -> float:
    values: list[float] = []
    for row in attention_grid if isinstance(attention_grid, list) else []:
        if not isinstance(row, list):
            continue
        for value in row:
            try:
                values.append(max(0.0, float(value)))
            except (TypeError, ValueError):
                continue
    if len(values) < 2:
        return 0.0
    total = sum(values)
    if total <= 0:
        return 0.0
    entropy = -sum((value / total) * math.log((value / total) + 1e-9) for value in values)
    return _clamp01(entropy / math.log(len(values)))


def _hierarchy_clarity(visual_regions: list[Any], attention_metrics: dict[str, Any]) -> float:
    focus_clarity = _metric01(attention_metrics.get("focus_clarity"))
    areas: list[float] = []
    for region in visual_regions:
        bbox = _bbox_values(region)
        if bbox is None:
            continue
        _, _, w, h = bbox
        areas.append(w * h)
    if len(areas) < 2:
        return _clamp01(0.55 + focus_clarity * 0.35)
    areas.sort(reverse=True)
    top_ratio = areas[0] / max(1.0, sum(areas[:5]))
    separation = _clamp01((areas[0] - areas[1]) / max(1.0, areas[0]))
    return _clamp01(top_ratio * 0.45 + separation * 0.25 + focus_clarity * 0.30)


def _uppercase_ratio(raw_text: str) -> float:
    letters = [char for char in raw_text if char.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for char in letters if char.isupper()) / len(letters)


def compute_asset_signals(
    text_blocks: list[Any] | None = None,
    visual_regions: list[Any] | None = None,
    attention_grid: list[Any] | None = None,
    attention_metrics: dict[str, Any] | None = None,
) -> dict[str, float]:
    """Compute stable 0-100 asset signals from persisted vision data only."""
    safe_text_blocks = text_blocks if isinstance(text_blocks, list) else []
    safe_visual_regions = visual_regions if isinstance(visual_regions, list) else []
    safe_attention_grid = attention_grid if isinstance(attention_grid, list) else []
    safe_attention_metrics = attention_metrics if isinstance(attention_metrics, dict) else {}

    text_values, normalized_text, raw_text = _text_from_blocks(safe_text_blocks)
    token_count = max(1, len(re.findall(r"\b[\w%$!]+\b", normalized_text)))
    region_count = len(safe_visual_regions)
    text_block_count = len(text_values)

    text_density = _text_density(safe_text_blocks, safe_visual_regions, safe_attention_grid)
    attention_dispersion = _metric01(safe_attention_metrics.get("attention_dispersion")) or _grid_dispersion(safe_attention_grid)
    visual_noise = _metric01(safe_attention_metrics.get("visual_noise"))
    focus_clarity = _metric01(safe_attention_metrics.get("focus_clarity"))
    hierarchy_clarity = _hierarchy_clarity(safe_visual_regions, safe_attention_metrics)
    region_dispersion = _region_dispersion(safe_visual_regions, safe_attention_grid)

    promo_count = _count_terms(normalized_text, PROMO_TERMS)
    price_count = _count_terms(normalized_text, PRICE_TERMS) + _count_price_patterns(normalized_text)
    cta_count = _count_terms(normalized_text, CTA_TERMS)
    urgency_count = _count_terms(normalized_text, URGENCY_TERMS)
    brand_count = _count_terms(normalized_text, BRAND_TERMS)
    symbol_count = normalized_text.count("%") + normalized_text.count("$") + normalized_text.count("!")

    promo_presence = 1.0 if promo_count > 0 or "%" in normalized_text else 0.0
    commercial_pressure = _clamp01(
        min(1.0, promo_count / 2.0) * 0.28
        + min(1.0, price_count / 2.0) * 0.28
        + min(1.0, cta_count / 2.0) * 0.22
        + min(1.0, urgency_count / 2.0) * 0.12
        + min(1.0, symbol_count / 3.0) * 0.10
    )
    conversion_intent = _clamp01(commercial_pressure * 0.82 + min(1.0, text_block_count / 12.0) * 0.10 + promo_presence * 0.08)

    language_stress = _clamp01(
        min(1.0, urgency_count / token_count * 4.0) * 0.30
        + min(1.0, cta_count / token_count * 3.0) * 0.22
        + min(1.0, promo_count / token_count * 2.5) * 0.20
        + _uppercase_ratio(raw_text) * 0.16
        + min(1.0, symbol_count / 3.0) * 0.12
    )

    layout_density = _clamp01(
        min(1.0, region_count / 16.0) * 0.34
        + min(1.0, text_block_count / 14.0) * 0.20
        + text_density * 0.18
        + region_dispersion * 0.14
        + (1.0 - hierarchy_clarity) * 0.14
    )
    visual_load = _clamp01(
        layout_density * 0.34
        + min(1.0, region_count / 20.0) * 0.18
        + min(1.0, text_block_count / 16.0) * 0.16
        + text_density * 0.14
        + attention_dispersion * 0.10
        + visual_noise * 0.08
    )
    brand_signal_clarity = _clamp01(
        hierarchy_clarity * 0.42
        + focus_clarity * 0.28
        + min(1.0, brand_count / 2.0) * 0.20
        + (1.0 - commercial_pressure) * 0.10
    )

    return {
        "visual_load": _score(visual_load),
        "conversion_intent": _score(conversion_intent),
        "language_stress": _score(language_stress),
        "layout_density": _score(layout_density),
        "attention_dispersion": _score(attention_dispersion),
        "brand_signal_clarity": _score(brand_signal_clarity),
        "text_density": _score(text_density),
        "promo_presence": _score(promo_presence),
        "hierarchy_clarity": _score(hierarchy_clarity),
        "commercial_pressure": _score(commercial_pressure),
    }


def attach_asset_signals(vision_data: dict[str, Any]) -> dict[str, Any]:
    """Return vision data with a refreshed asset_signals payload."""
    vision_data["asset_signals"] = compute_asset_signals(
        text_blocks=vision_data.get("text_blocks"),
        visual_regions=vision_data.get("visual_regions"),
        attention_grid=vision_data.get("attention_grid"),
        attention_metrics=vision_data.get("attention_metrics"),
    )
    return vision_data
