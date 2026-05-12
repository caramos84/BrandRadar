import re
import unicodedata
from dataclasses import dataclass
from typing import Any

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
IGNORE_LAYOUT_TERMS = {"cierre", "portada", "carr", "carousel", "cr", "st", "lp", "yt", "historia", "post", "story", "feed"}
PRODUCT_HINTS = {"product", "producto", "pack", "bottle", "shoe", "phone", "laptop"}
LOGO_HINTS = {"logo", "brandmark", "isotype", "wordmark"}


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


def _clamp_score(value: float) -> float:
    return max(0.0, min(100.0, round(value, 2)))


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

    layout_density = min(1.0, (region_count * 0.12) + (text_density * 0.6))

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

    conversion_signal_score = _clamp_score(conversion_signal_raw)

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
        "layout_density": round(layout_density, 4),
        "analysis_cluster_label": analysis_cluster_label,
    }
