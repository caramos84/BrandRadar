import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Iterable

PROMO_TERMS = {
    "promo", "promocion", "oferta", "ofert", "ofer", "ofe", "descuento", "dcto", "dto", "ahorro", "ahorra",
    "rebaja", "sale", "off", "gratis", "free", "2x1", "3x2", "%",
}
PRICE_TERMS = {
    "precio", "price", "desde", "solo", "antes", "ahora", "por", "ahorro", "ahorra", "$", "cop", "pesos",
}
CTA_TERMS = {
    "compra", "comprar", "conoce", "descubre", "aprovecha", "participa", "reclama", "redime", "lleva", "pide",
    "shop", "buy", "get", "claim", "order", "learn more",
}
LEGAL_TERMS = {
    "legal", "tyc", "t&c", "terminos", "condiciones", "restricciones", "aplica", "vigencia", "valido",
}
LEGAL_FOOTER_TERMS = {
    "aplican terminos", "terminos y condiciones", "condiciones", "publicidad valida", "vigencia",
    "cobertura limitada", "aplica para", "tope maximo", "valido hasta", "terminos condiciones",
    "restricciones aplican", "sujeto a", "exclusiones aplican", "no aplicable",
}
IGNORE_LAYOUT_TERMS = {"cierre", "portada", "carr", "carousel", "cr", "st", "lp", "yt", "historia", "post", "story", "feed"}
PRODUCT_HINTS = {"product", "producto", "pack", "bottle", "shoe", "phone", "laptop"}
LOGO_HINTS = {"logo", "brandmark", "isotype", "wordmark"}

LANGUAGE_STRESS_PROMO_WORDS = {
    "dto", "descuento", "promo", "oferta", "gratis", "ahorra", "rebaja", "2x1", "3x2", "precio", "temporada",
}
LANGUAGE_STRESS_CTA_WORDS = {
    "compra", "lleva", "obtén", "obtenga", "participa", "aprovecha", "descubre",
}
LANGUAGE_STRESS_URGENCY_WORDS = [
    "hoy", "ya", "último", "últimos", "ahora", "tiempo limitado", "solo hoy", "por tiempo limitado",
]
LANGUAGE_STRESS_SYMBOLS = "%$!"


@dataclass
class FeatureInput:
    original_filename: str
    width: int | None
    height: int | None
    size_bytes: int
    text_blocks: list[str] | None = None
    regions: list[dict[str, Any]] | None = None


def _normalize_text(raw_text: str) -> str:
    lower = raw_text.lower()
    normalized = unicodedata.normalize("NFKD", lower)
    without_accents = "".join(char for char in normalized if not unicodedata.combining(char))
    spaced = re.sub(r"[_\-\.]", " ", without_accents)
    collapsed = re.sub(r"\s+", " ", spaced).strip()
    return collapsed


def _contains_any_term(text: str, terms: set[str]) -> bool:
    return any(term in text for term in terms)


def _count_text_terms(normalized_text: str, terms: Iterable[str]) -> int:
    count = 0
    for term in terms:
        if " " in term:
            count += normalized_text.count(term)
        else:
            count += len(re.findall(rf"\b{re.escape(term)}\b", normalized_text))
    return count


def _compute_uppercase_ratio(raw_text: str) -> float:
    letters = [char for char in raw_text if char.isalpha()]
    if not letters:
        return 0.0
    uppercase_letters = sum(1 for char in letters if char.isupper())
    return uppercase_letters / len(letters)


def _clamp_score(value: float) -> float:
    return max(0.0, min(100.0, round(value, 2)))


def normalize_ocr_text(raw_text: str) -> str:
    """Normalize OCR text: lowercase, remove accents, deduplicate spaces."""
    lower = raw_text.lower()
    normalized = unicodedata.normalize("NFKD", lower)
    without_accents = "".join(char for char in normalized if not unicodedata.combining(char))
    spaced = re.sub(r"[_\-\.]", " ", without_accents)
    collapsed = re.sub(r"\s+", " ", spaced).strip()
    return collapsed


def count_regex_matches(text: str, pattern: str) -> int:
    """Count regex matches in text."""
    try:
        return len(re.findall(pattern, text, re.IGNORECASE))
    except Exception:
        return 0


def compute_legal_noise_ratio(normalized_text: str) -> float:
    """Compute the ratio of legal/footer terms to total meaningful tokens."""
    legal_count = 0
    for term in LEGAL_FOOTER_TERMS:
        legal_count += normalized_text.count(term)
    
    tokens = len(re.findall(r"\b\w+\b", normalized_text))
    if tokens == 0:
        return 0.0
    
    return min(1.0, legal_count / max(1, tokens / 5))


def compute_commercial_signal_score(normalized_text: str, has_promo: bool, has_price: bool, has_cta: bool, legal_noise_ratio: float) -> float:
    """
    Compute a commercial signal score based on OCR text quality.
    
    Focuses on:
    - Price patterns: $19.900, $ 19990, 20%, 35%, etc.
    - Promo terms: descuento, dto, oferta, promo, ahorro, gratis, 2x1, 3x2
    - CTA: compra, lleva, aprovecha, pide, obtén
    - Urgency: solo hoy, hoy, ahora, tiempo limitado
    
    Reduces score if text is mostly legal/footer language.
    """
    score = 0.0
    
    price_pattern_count = count_regex_matches(
        normalized_text, r"\$\s*[\d.,]+|[\d]+\s*%|\d+\s*\$"
    )
    if price_pattern_count > 0:
        score += min(28, price_pattern_count * 14)
    elif has_price:
        score += 18
    
    promo_pattern_count = count_regex_matches(
        normalized_text, r"(descuento|dto|dcto|oferta|promo|ahorro|ahorra|gratis|2x1|3x2)"
    )
    if promo_pattern_count > 0:
        score += min(26, promo_pattern_count * 13)
    elif has_promo:
        score += 20
    
    cta_pattern_count = count_regex_matches(
        normalized_text, r"(compra|lleva|aprovecha|pide|obten|obtenga|comprar|participa)"
    )
    if cta_pattern_count > 0:
        score += min(24, cta_pattern_count * 12)
    elif has_cta:
        score += 18
    
    urgency_count = _count_text_terms(normalized_text, LANGUAGE_STRESS_URGENCY_WORDS)
    if urgency_count > 0:
        score += min(12, urgency_count * 6)
    
    symbol_count = normalized_text.count("%") + normalized_text.count("$") + normalized_text.count("!")
    if symbol_count > 0:
        score += min(8, symbol_count * 2.6)
    
    if legal_noise_ratio > 0.5:
        score *= 0.4
    elif legal_noise_ratio > 0.25:
        score *= 0.7
    
    return _clamp_score(score)


def _compute_cluster_label(conversion_signal_score: float, visual_load_score: float, product_candidate_detected: bool, text_density: float) -> str:
    if conversion_signal_score >= 55 and visual_load_score >= 55:
        return "Promotional Heavy"
    if conversion_signal_score >= 55 and visual_load_score < 55:
        return "Clean Conversion"
    if product_candidate_detected and text_density <= 0.18:
        return "Product Hero"
    if conversion_signal_score >= 25 and visual_load_score >= 45:
        return "Informational Dense"
    if conversion_signal_score >= 25 and visual_load_score < 45:
        return "Clean Conversion"
    if conversion_signal_score < 25 and visual_load_score < 40:
        return "Brand / Lifestyle"
    if visual_load_score >= 60:
        return "Informational Dense"
    return "Unclassified"


def compute_asset_features(asset: FeatureInput, optional_text_blocks: list[str] | None = None, optional_regions: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    text_blocks = optional_text_blocks if optional_text_blocks is not None else (asset.text_blocks or [])
    regions = optional_regions if optional_regions is not None else (asset.regions or [])

    width = asset.width or 0
    height = asset.height or 0
    pixel_area = width * height if width and height else None
    aspect_ratio = round(width / height, 4) if width and height else None

    source_text = f"{asset.original_filename} {' '.join(text_blocks)}"
    normalized_text = _normalize_text(source_text)

    has_layout_only_terms = _contains_any_term(normalized_text, IGNORE_LAYOUT_TERMS)
    cta_detected = _contains_any_term(normalized_text, CTA_TERMS)
    price_detected = _contains_any_term(normalized_text, PRICE_TERMS)
    promo_detected = _contains_any_term(normalized_text, PROMO_TERMS)
    legal_detected = _contains_any_term(normalized_text, LEGAL_TERMS)
    product_candidate_detected = _contains_any_term(normalized_text, PRODUCT_HINTS)
    logo_candidate_detected = _contains_any_term(normalized_text, LOGO_HINTS)

    text_block_count = len([text for text in text_blocks if text.strip()])
    region_count = len(regions)

    if pixel_area and pixel_area > 0:
        text_density = min(1.0, (text_block_count * 45000) / pixel_area)
    else:
        text_density = 0.0

    region_count_factor = min(1.0, region_count / 12.0)
    text_block_factor = min(1.0, text_block_count / 12.0)
    text_complexity = min(1.0, text_density * 0.65 + text_block_factor * 0.35)

    max_width = width or 1
    max_height = height or 1
    diagonal = (max_width ** 2 + max_height ** 2) ** 0.5
    image_center_x = max_width / 2
    image_center_y = max_height / 2

    centroids: list[tuple[float, float, float]] = []
    for region in regions:
        bbox = region.get("bbox")
        if not bbox or len(bbox) < 4:
            continue
        x, y, w, h = bbox[0], bbox[1], bbox[2], bbox[3]
        cx = x + w / 2
        cy = y + h / 2
        area = max(1.0, float(w) * float(h))
        centroids.append((cx, cy, area))

    if len(centroids) > 1:
        distances: list[float] = []
        for index, (cx, cy, _) in enumerate(centroids):
            for other_cx, other_cy, _ in centroids[index + 1 :]:
                distances.append(((cx - other_cx) ** 2 + (cy - other_cy) ** 2) ** 0.5)
        avg_pair_distance = sum(distances) / len(distances) if distances else 0.0
        dispersion = min(1.0, avg_pair_distance / max(1.0, diagonal * 0.6))
    else:
        dispersion = 0.0

    total_area = sum(area for _, _, area in centroids) or 1.0
    left_mass = sum(area for cx, _, area in centroids if cx < image_center_x)
    top_mass = sum(area for _, cy, area in centroids if cy < image_center_y)
    balance_lr = abs(left_mass - (total_area - left_mass)) / total_area
    balance_tb = abs(top_mass - (total_area - top_mass)) / total_area
    balance_proxy = min(1.0, (balance_lr + balance_tb) / 2)

    fragmentation = region_count_factor
    layout_complexity_raw = (
        fragmentation * 35
        + text_complexity * 25
        + dispersion * 20
        + balance_proxy * 20
    )
    layout_complexity_score = _clamp_score(layout_complexity_raw)

    area_factor = min(1.0, (pixel_area or 0) / 6_000_000)
    size_factor = min(1.0, asset.size_bytes / 4_000_000)
    visual_load_raw = (
        area_factor * 24
        + size_factor * 22
        + min(1.0, region_count / 10) * 20
        + min(1.0, text_block_count / 12) * 18
        + text_density * 16
    )
    visual_load_score = _clamp_score(visual_load_raw)

    conversion_signal_raw = 0.0
    if promo_detected:
        conversion_signal_raw += 24
    if price_detected:
        conversion_signal_raw += 22
    if cta_detected:
        conversion_signal_raw += 22
    if legal_detected:
        conversion_signal_raw += 8

    if text_block_count > 0:
        conversion_signal_raw += min(12, text_block_count * 1.8)
    if text_density > 0.2:
        conversion_signal_raw += 6
    if "!" in normalized_text or "%" in normalized_text:
        conversion_signal_raw += 6

    if has_layout_only_terms and not (promo_detected or price_detected or cta_detected or legal_detected):
        conversion_signal_raw -= 12

    legal_noise_ratio = compute_legal_noise_ratio(normalized_text)
    commercial_signal = compute_commercial_signal_score(
        normalized_text, promo_detected, price_detected, cta_detected, legal_noise_ratio
    )
    
    if legal_noise_ratio > 0.5 and not price_detected and not promo_detected:
        conversion_signal_raw = min(conversion_signal_raw, 15)
    
    conversion_signal_score = _clamp_score(max(conversion_signal_raw, commercial_signal))

    language_stress_source_text = " ".join(text_blocks) if text_blocks else asset.original_filename
    uppercase_ratio = _compute_uppercase_ratio(language_stress_source_text)
    token_count = max(1, len(re.findall(r"\b[\w%$!]+\b", normalized_text)))
    urgency_count = _count_text_terms(normalized_text, LANGUAGE_STRESS_URGENCY_WORDS)
    cta_count = _count_text_terms(normalized_text, LANGUAGE_STRESS_CTA_WORDS)
    promo_count = _count_text_terms(normalized_text, LANGUAGE_STRESS_PROMO_WORDS)
    symbol_count = sum(normalized_text.count(symbol) for symbol in LANGUAGE_STRESS_SYMBOLS)

    urgency_density = min(1.0, (urgency_count / token_count) * 4.0)
    cta_density = min(1.0, (cta_count / token_count) * 3.0)
    promo_pressure = min(1.0, (promo_count / token_count) * 2.5)
    symbol_pressure = min(1.0, symbol_count / 2.0)

    language_stress_raw = (
        urgency_density * 30
        + cta_density * 25
        + promo_pressure * 20
        + uppercase_ratio * 15
        + symbol_pressure * 10
    )
    language_stress_score = _clamp_score(language_stress_raw)

    analysis_cluster_label = _compute_cluster_label(
        conversion_signal_score=conversion_signal_score,
        visual_load_score=visual_load_score,
        product_candidate_detected=product_candidate_detected,
        text_density=text_density,
    )

    return {
        "aspect_ratio": aspect_ratio,
        "pixel_area": pixel_area,
        "visual_load_score": visual_load_score,
        "conversion_signal_score": conversion_signal_score,
        "text_density": round(text_density, 4),
        "region_count": region_count,
        "text_block_count": text_block_count,
        "cta_detected": cta_detected,
        "price_detected": price_detected,
        "promo_detected": promo_detected,
        "legal_detected": legal_detected,
        "product_candidate_detected": product_candidate_detected,
        "logo_candidate_detected": logo_candidate_detected,
        "layout_density": round(layout_complexity_score, 4),
        "analysis_cluster_label": analysis_cluster_label,
        "language_stress_score": language_stress_score,
    }
