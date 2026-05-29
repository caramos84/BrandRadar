import math
import re
import unicodedata
from typing import Any

PROMO_TERMS = {
    "promo", "promocion", "promoción", "oferta", "ofert", "ofer", "ofe", "descuento", "descuentos", "dcto",
    "dto", "ahorro", "ahorra", "rebaja", "sale", "off", "gratis", "free", "2x1", "3x2", "black days",
    "black friday", "exclusivo", "exclusivos",
}
PRICE_TERMS = {"precio", "price", "desde", "solo", "antes", "ahora", "por", "hasta", "$", "cop", "pesos"}
CTA_TERMS = {
    "compra", "comprar", "conoce", "descubre", "aprovecha", "participa", "reclama", "redime", "lleva", "pide",
    "entra", "paga", "estrena", "shop", "buy", "get", "claim", "order", "learn more",
}
URGENCY_TERMS = {"hoy", "ya", "ultimo", "ultimos", "ahora", "tiempo limitado", "solo hoy", "por tiempo limitado"}
FINANCING_TERMS = {"cuota", "cuotas", "financia", "financiacion", "financiación", "credito", "crédito", "paga"}
CONDITION_TERMS = {"aplica", "condiciones", "valido", "válido", "valida", "válida", "vigencia", "hasta", "desde"}
LEGAL_TERMS = {"legal", "terminos", "términos", "condiciones", "restricciones", "aplica", "vigencia", "valido", "válido"}
BRAND_TERMS = {"logo", "marca", "marcas", "brand", "brandmark", "isotype", "wordmark"}
PRODUCT_TERMS = {"producto", "productos", "coleccion", "colección", "linea", "línea", "nuevo", "nueva", "pack", "plan", "planes"}

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
        normalized_term = _normalize_text(term)
        if " " in normalized_term:
            count += text.count(normalized_term)
        else:
            count += len(re.findall(rf"\b{re.escape(normalized_term)}\b", text))
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

def _canvas_bounds(text_blocks: list[Any], visual_regions: list[Any]) -> tuple[float, float]:
    max_x = 0.0
    max_y = 0.0
    for item in [*text_blocks, *visual_regions]:
        bbox = _bbox_values(item)
        if bbox is None:
            continue
        x, y, w, h = bbox
        max_x = max(max_x, x + w)
        max_y = max(max_y, y + h)
    return max_x, max_y

def _canvas_area(text_blocks: list[Any], visual_regions: list[Any], attention_grid: list[Any]) -> float:
    max_x, max_y = _canvas_bounds(text_blocks, visual_regions)
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
    for block in text_blocks:
        bbox = _bbox_values(block)
        if bbox is None:
            continue
        _, _, w, h = bbox
        text_area += w * h
    if text_area > 0:
        return _clamp01(text_area / _canvas_area(text_blocks, visual_regions, attention_grid))
    return _clamp01(len(text_blocks) / 18.0)

def _attention_values(attention_grid: list[Any]) -> list[float]:
    values: list[float] = []
    for row in attention_grid if isinstance(attention_grid, list) else []:
        if not isinstance(row, list):
            continue
        for value in row:
            try:
                values.append(_clamp01(float(value)))
            except (TypeError, ValueError):
                continue
    return values

def _grid_dispersion(attention_grid: list[Any]) -> float:
    values = _attention_values(attention_grid)
    if len(values) < 2:
        return 0.0
    total = sum(values)
    if total <= 0:
        return 0.0
    entropy = -sum((value / total) * math.log((value / total) + 1e-9) for value in values if value > 0)
    return _clamp01(entropy / math.log(len(values)))

def _active_attention_ratio(attention_grid: list[Any]) -> float:
    values = _attention_values(attention_grid)
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    threshold = max(0.18, mean + math.sqrt(variance) * 0.25)
    return sum(1 for value in values if value >= threshold) / len(values)

def _attention_top_spread(attention_grid: list[Any], attention_metrics: dict[str, Any]) -> float:
    primary = _metric01(attention_metrics.get("primary_attention_score"))
    top3 = _metric01(attention_metrics.get("top3_attention_mean"))
    if primary <= 0.0:
        values = sorted(_attention_values(attention_grid), reverse=True)
        if not values:
            return 0.0
        primary = values[0]
        top3 = sum(values[:3]) / min(3, len(values))
    if primary <= 0.0:
        return 0.0
    # If the top three cells are close to the primary cell, attention is spread across multiple hotspots.
    return _clamp01((top3 / primary - 0.45) / 0.55)

def _region_dispersion(visual_regions: list[Any], attention_grid: list[Any]) -> float:
    centroids: list[tuple[float, float, float]] = []
    for region in visual_regions:
        bbox = _bbox_values(region)
        if bbox is None:
            continue
        x, y, w, h = bbox
        centroids.append((x + w / 2.0, y + h / 2.0, max(1.0, w * h)))
    if len(centroids) < 2:
        return _grid_dispersion(attention_grid) * 0.6
    max_x = max(cx for cx, _, _ in centroids)
    max_y = max(cy for _, cy, _ in centroids)
    diagonal = max(1.0, math.hypot(max_x, max_y))
    distances: list[float] = []
    for index, (cx, cy, _) in enumerate(centroids):
        for other_cx, other_cy, _ in centroids[index + 1:]:
            distances.append(math.hypot(cx - other_cx, cy - other_cy))
    return _clamp01((sum(distances) / len(distances)) / (diagonal * 0.7)) if distances else 0.0

def _wide_composition_factor(text_blocks: list[Any], visual_regions: list[Any]) -> float:
    max_x, max_y = _canvas_bounds(text_blocks, visual_regions)
    if max_x <= 0 or max_y <= 0:
        return 0.0
    aspect = max_x / max(1.0, max_y)
    return _clamp01((aspect - 1.25) / 2.25)

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
        return _clamp01(0.45 + focus_clarity * 0.40)
    areas.sort(reverse=True)
    top_ratio = areas[0] / max(1.0, sum(areas[:6]))
    separation = _clamp01((areas[0] - areas[1]) / max(1.0, areas[0]))
    return _clamp01(top_ratio * 0.42 + separation * 0.28 + focus_clarity * 0.30)

def _uppercase_ratio(raw_text: str) -> float:
    letters = [char for char in raw_text if char.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for char in letters if char.isupper()) / len(letters)

def _attention_dispersion_score(
    attention_grid: list[Any],
    attention_metrics: dict[str, Any],
    visual_regions: list[Any],
    visual_noise: float,
    focus_clarity: float,
    region_dispersion: float,
) -> float:
    active_ratio = _active_attention_ratio(attention_grid)
    top_spread = _attention_top_spread(attention_grid, attention_metrics)
    region_factor = _clamp01(len(visual_regions) / 14.0)
    focus_inverse = 1.0 - focus_clarity if attention_metrics.get("focus_clarity") is not None else 0.35
    dispersion = (
        active_ratio * 0.22
        + visual_noise * 0.20
        + focus_inverse * 0.22
        + top_spread * 0.16
        + region_factor * 0.12
        + region_dispersion * 0.08
    )
    if active_ratio > 0.0 or visual_regions:
        dispersion = max(dispersion, 0.20)
    if len(visual_regions) <= 2 and focus_clarity >= 0.65 and active_ratio <= 0.30:
        dispersion = min(dispersion, 0.45)
    elif len(visual_regions) <= 6 and visual_noise < 0.65:
        dispersion = min(dispersion, 0.70)
    if not (active_ratio > 0.78 and visual_noise > 0.72 and focus_clarity < 0.30 and len(visual_regions) >= 14):
        dispersion = min(dispersion, 0.90)
    return _clamp01(dispersion)

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
    tokens = re.findall(r"\b[\w%$!]+\b", normalized_text)
    token_count = max(1, len(tokens))
    region_count = len(safe_visual_regions)
    text_block_count = len(text_values)

    text_density = _text_density(safe_text_blocks, safe_visual_regions, safe_attention_grid)
    visual_noise = _metric01(safe_attention_metrics.get("visual_noise"))
    focus_clarity = _metric01(safe_attention_metrics.get("focus_clarity"))
    hierarchy_clarity = _hierarchy_clarity(safe_visual_regions, safe_attention_metrics)
    region_dispersion = _region_dispersion(safe_visual_regions, safe_attention_grid)
    active_attention_ratio = _active_attention_ratio(safe_attention_grid)
    attention_dispersion = _attention_dispersion_score(
        safe_attention_grid,
        safe_attention_metrics,
        safe_visual_regions,
        visual_noise,
        focus_clarity,
        region_dispersion,
    )

    promo_count = _count_terms(normalized_text, PROMO_TERMS)
    price_count = _count_terms(normalized_text, PRICE_TERMS) + _count_price_patterns(normalized_text)
    cta_count = _count_terms(normalized_text, CTA_TERMS)
    urgency_count = _count_terms(normalized_text, URGENCY_TERMS)
    financing_count = _count_terms(normalized_text, FINANCING_TERMS)
    condition_count = _count_terms(normalized_text, CONDITION_TERMS)
    legal_count = _count_terms(normalized_text, LEGAL_TERMS)
    brand_count = _count_terms(normalized_text, BRAND_TERMS)
    product_count = _count_terms(normalized_text, PRODUCT_TERMS)
    symbol_count = normalized_text.count("%") + normalized_text.count("$") + normalized_text.count("!")
    punctuation_count = len(re.findall(r"[!¡?¿%$*.,:;]", raw_text))
    numeric_tokens = sum(1 for token in tokens if any(char.isdigit() for char in token))

    promo_presence = 1.0 if promo_count > 0 or "%" in normalized_text else 0.0
    base_commercial = _clamp01(
        min(1.0, promo_count / 2.0) * 0.24
        + min(1.0, price_count / 2.0) * 0.18
        + min(1.0, cta_count / 2.0) * 0.20
        + min(1.0, financing_count / 2.0) * 0.14
        + min(1.0, urgency_count / 2.0) * 0.08
        + min(1.0, condition_count / 3.0) * 0.08
        + min(1.0, symbol_count / 3.0) * 0.08
    )
    combination_bonus = 0.0
    if promo_count and cta_count:
        combination_bonus += 0.10
    if financing_count and cta_count:
        combination_bonus += 0.11
    if financing_count and (brand_count or product_count):
        combination_bonus += 0.08
    if _count_terms(normalized_text, {"sale", "black days", "black friday"}) and cta_count:
        combination_bonus += 0.08
    commercial_pressure = _clamp01(base_commercial + combination_bonus * 0.65)
    conversion_intent = _clamp01(
        commercial_pressure * 0.78
        + promo_presence * 0.08
        + min(1.0, text_block_count / 10.0) * 0.06
        + min(1.0, (brand_count + product_count) / 3.0) * 0.08
    )

    word_load = _clamp01((token_count - 3) / 32.0)
    numeric_density = _clamp01((numeric_tokens / token_count) * 3.0)
    punctuation_density = _clamp01((punctuation_count / token_count) * 2.0)
    financing_pressure = _clamp01(financing_count / 2.0)
    condition_pressure = _clamp01((condition_count + legal_count) / 4.0)
    language_stress = _clamp01(
        word_load * 0.18
        + numeric_density * 0.15
        + _uppercase_ratio(raw_text) * 0.16
        + punctuation_density * 0.13
        + financing_pressure * 0.17
        + condition_pressure * 0.13
        + min(1.0, (promo_count + cta_count + urgency_count) / 4.0) * 0.08
    )

    layout_density = _clamp01(
        min(1.0, region_count / 12.0) * 0.28
        + min(1.0, text_block_count / 10.0) * 0.18
        + text_density * 0.16
        + region_dispersion * 0.14
        + active_attention_ratio * 0.12
        + _wide_composition_factor(safe_text_blocks, safe_visual_regions) * 0.08
        + (1.0 - hierarchy_clarity) * 0.04
    )
    visual_load = _clamp01(
        layout_density * 0.38
        + min(1.0, region_count / 18.0) * 0.16
        + min(1.0, text_block_count / 14.0) * 0.14
        + text_density * 0.12
        + attention_dispersion * 0.12
        + visual_noise * 0.08
    )

    brand_evidence = _clamp01(brand_count / 2.0)
    uncluttered = _clamp01(
        1.0
        - visual_noise * 0.28
        - text_density * 0.24
        - min(1.0, max(0, region_count - 4) / 12.0) * 0.24
        - commercial_pressure * 0.14
    )
    if brand_evidence <= 0.0:
        brand_signal_clarity = _clamp01(hierarchy_clarity * 0.20 + focus_clarity * 0.12 + uncluttered * 0.08)
    else:
        brand_signal_clarity = _clamp01(
            brand_evidence * 0.34
            + hierarchy_clarity * 0.26
            + focus_clarity * 0.20
            + uncluttered * 0.20
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
