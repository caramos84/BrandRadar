from __future__ import annotations

import math
import re
import unicodedata
from typing import Any

SECTIONS = ("headline", "body", "legal", "cta", "price_offer", "other")
TARGET_LANGUAGES = [
    {"code": "es", "label": "Spanish", "base": 1.15},
    {"code": "pt", "label": "Portuguese", "base": 1.20},
    {"code": "de", "label": "German", "base": 1.35},
    {"code": "fr", "label": "French", "base": 1.25},
    {"code": "ja", "label": "Japanese", "base": 1.10},
    {"code": "ko", "label": "Korean", "base": 1.05},
    {"code": "zh", "label": "Chinese", "base": 1.00},
]

PRICE_TERMS = {
    "price", "sale", "offer", "save", "discount", "off", "free", "promo", "deal", "cuota", "cuotas",
    "descuento", "dcto", "dto", "oferta", "black friday", "black days", "%", "$",
}
CTA_TERMS = {
    "buy", "shop", "now", "order", "learn more", "claim", "get", "compra", "comprar", "conoce", "entra",
    "aprovecha", "receive", "recibe", "usa", "usando", "lleva",
}
LEGAL_TERMS = {
    "legal", "terms", "conditions", "copyright", "trademark", "responsibly", "responsibility", "applies",
    "restrictions", "vigencia", "valido", "valida", "terminos", "condiciones", "drink responsibly",
}

LAYOUT_TYPE_TO_SECTION = {
    "Headline": "headline",
    "Legal / Footer": "legal",
    "CTA": "cta",
    "Price / Offer": "price_offer",
}


def _safe_empty(baseline_language: str = "en") -> dict[str, Any]:
    return {
        "version": 1,
        "baseline_language": baseline_language,
        "languages": [],
        "summary": {
            "overall_status": "unknown",
            "critical_languages": [],
            "warning_languages": [],
            "comfortable_languages": [],
            "worst_language": None,
            "max_expansion_pct": 0,
            "primary_risk_sections": [],
        },
        "reading": "",
    }


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


def _block_text(block: dict[str, Any]) -> str:
    return str(block.get("text", "")).strip() if isinstance(block, dict) else ""


def _valid_bbox(block: dict[str, Any]) -> tuple[float, float, float, float] | None:
    bbox = block.get("bbox") if isinstance(block, dict) else None
    if not isinstance(bbox, (list, tuple)) or len(bbox) < 4:
        return None
    try:
        x, y, w, h = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
    except (TypeError, ValueError):
        return None
    if w <= 0 or h <= 0:
        return None
    return x, y, w, h


def _classify_text(text: str, is_first: bool = False) -> str:
    normalized = _normalize_text(text)
    if not normalized:
        return "other"
    if _count_terms(normalized, LEGAL_TERMS) > 0 or len(normalized) > 120 and re.search(r"\b(applies|terms|conditions|copyright|trademark)\b", normalized):
        return "legal"
    if _count_terms(normalized, PRICE_TERMS) > 0 or re.search(r"\$\s*\d|\d+\s*%", normalized):
        return "price_offer"
    if _count_terms(normalized, CTA_TERMS) > 0:
        return "cta"
    word_count = len(re.findall(r"\b\w+\b", normalized))
    if is_first or (2 <= word_count <= 8 and len(normalized) <= 70):
        return "headline"
    if word_count >= 9:
        return "body"
    return "other"


def _layout_blocks(layout_analysis: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(layout_analysis, dict):
        return []
    blocks = layout_analysis.get("blocks")
    return blocks if isinstance(blocks, list) else []


def _center_in_layout(text_block: dict[str, Any], layout_block: dict[str, Any]) -> bool:
    bbox = _valid_bbox(text_block)
    if bbox is None:
        return False
    x, y, w, h = bbox
    cx, cy = x + w / 2, y + h / 2
    try:
        lx = float(layout_block.get("x_px", 0))
        ly = float(layout_block.get("y_px", 0))
        lw = float(layout_block.get("width_px", 0))
        lh = float(layout_block.get("height_px", 0))
    except (TypeError, ValueError):
        return False
    return lx <= cx <= lx + lw and ly <= cy <= ly + lh


def _section_for_text_block(block: dict[str, Any], layout_blocks: list[dict[str, Any]], is_first: bool) -> str:
    text = _block_text(block)
    for layout_block in layout_blocks:
        layout_type = str(layout_block.get("type", ""))
        mapped = LAYOUT_TYPE_TO_SECTION.get(layout_type)
        if mapped and _center_in_layout(block, layout_block):
            return mapped
    return _classify_text(text, is_first=is_first)


def _layout_section_constraints(layout_blocks: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    constraints: dict[str, dict[str, float]] = {}
    for block in layout_blocks:
        section = LAYOUT_TYPE_TO_SECTION.get(str(block.get("type", "")))
        if not section:
            continue
        try:
            area_pct = float(block.get("area_pct", 0.0))
            width_px = float(block.get("width_px", 0.0))
            height_px = float(block.get("height_px", 0.0))
        except (TypeError, ValueError):
            continue
        current = constraints.get(section)
        if current is None or area_pct > current["area_pct"]:
            constraints[section] = {"area_pct": area_pct, "width_px": width_px, "height_px": height_px}
    return constraints


def _build_sections(text_blocks: list[dict[str, Any]], layout_analysis: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    layout_blocks = _layout_blocks(layout_analysis)
    sections = {section: {"parts": [], "weight": _section_weight(section)} for section in SECTIONS}
    valid_texts = [_block_text(block) for block in text_blocks if isinstance(block, dict) and _block_text(block)]
    if not valid_texts:
        return {section: {"text": "", "chars": 0, "weight": data["weight"]} for section, data in sections.items()}

    assigned_headline = False
    for index, block in enumerate(text_blocks):
        if not isinstance(block, dict):
            continue
        text = _block_text(block)
        if not text:
            continue
        section = _section_for_text_block(block, layout_blocks, is_first=(index == 0 and not assigned_headline))
        if section == "headline":
            assigned_headline = True
        sections[section]["parts"].append(text)

    if not sections["headline"]["parts"]:
        # Promote the shortest strong phrase to headline if no explicit headline was found.
        candidates = [text for text in valid_texts if 2 <= len(text.split()) <= 9]
        if candidates:
            headline = candidates[0]
            sections["headline"]["parts"].append(headline)
            for section in SECTIONS:
                if section == "headline":
                    continue
                if headline in sections[section]["parts"]:
                    sections[section]["parts"].remove(headline)
                    break

    return {
        section: {
            "text": " ".join(data["parts"]).strip(),
            "chars": len(" ".join(data["parts"]).strip()),
            "weight": data["weight"],
        }
        for section, data in sections.items()
    }


def _section_weight(section: str) -> float:
    return {
        "headline": 1.35,
        "cta": 1.25,
        "price_offer": 1.20,
        "legal": 1.10,
        "body": 1.00,
        "other": 0.75,
    }[section]


def _status(expansion_pct: float) -> str:
    if expansion_pct <= 100:
        return "ok"
    if expansion_pct <= 120:
        return "warning"
    return "critical"


def _risk_level(status: str) -> str:
    return {"ok": "low", "warning": "medium", "critical": "high"}.get(status, "low")


def _claims_complexity(text: str) -> float:
    if not text:
        return 0.0
    separators = len(re.findall(r"[.!?;:|/]", text))
    pluses = text.count("+")
    return min(0.08, (separators + pluses) * 0.015)


def _uppercase_complexity(text: str, section: str, code: str) -> float:
    letters = [char for char in text if char.isalpha()]
    if not letters or section != "headline" or code not in {"es", "pt", "de", "fr"}:
        return 0.0
    ratio = sum(1 for char in letters if char.isupper()) / len(letters)
    words = len(text.split())
    if ratio >= 0.55 and words <= 8:
        return 0.07
    if ratio >= 0.30 and words <= 10:
        return 0.04
    return 0.0


def _section_factor(code: str, section: str, text: str) -> float:
    language = next(item for item in TARGET_LANGUAGES if item["code"] == code)
    factor = float(language["base"])
    normalized = _normalize_text(text)
    if section == "legal" and code in {"es", "pt", "de", "fr"}:
        factor += 0.10
    if section == "headline" and code in {"de", "fr", "pt"} and len(re.findall(r"\b\w+\b", normalized)) >= 5:
        factor += 0.05
    if section == "cta" and code in {"es", "pt", "fr"}:
        factor += 0.05
    if section == "price_offer" and code in {"de", "fr"} and (_count_terms(normalized, PRICE_TERMS) > 0 or re.search(r"\d", normalized)):
        factor += 0.05
    if section == "legal" and _count_terms(normalized, LEGAL_TERMS) > 0:
        factor += 0.06
    factor += _claims_complexity(text)
    factor += _uppercase_complexity(text, section, code)
    return max(0.75, factor)


def _estimated_text(text: str, estimated_chars: int) -> str:
    if not text or estimated_chars <= 0:
        return ""
    marker = " [estimated expansion]"
    if estimated_chars <= len(text):
        return text[:estimated_chars]
    repeated = text
    while len(repeated) < max(len(text), estimated_chars - len(marker)):
        repeated = f"{repeated} {text}"
    return f"{repeated[:max(0, estimated_chars - len(marker))].rstrip()}{marker}"


def _layout_risk(section: str, expansion_pct: float, constraints: dict[str, dict[str, float]]) -> str:
    status = _status(expansion_pct)
    if status == "ok":
        return "low"
    constraint = constraints.get(section)
    if not constraint:
        return _risk_level(status)
    area = constraint["area_pct"]
    height = constraint["height_px"]
    sensitive = section in {"headline", "cta", "price_offer"}
    if expansion_pct > 120 and (area < 8 or height < 44 or sensitive):
        return "high"
    if expansion_pct > 120:
        return "medium" if section == "legal" and area >= 5 else "high"
    if status == "warning" and (sensitive or area < 6):
        return "medium"
    return "low"


def _recommendations(code: str, label: str, sections: dict[str, dict[str, Any]]) -> list[str]:
    recommendations: list[str] = []
    critical_sections = [section for section, data in sections.items() if data.get("status") == "critical"]
    warning_sections = [section for section, data in sections.items() if data.get("status") == "warning"]
    if "headline" in critical_sections:
        recommendations.append(f"Shorten headline for {label} or create a localized headline variant.")
        recommendations.append("Create localized headline variant.")
    if "legal" in critical_sections or "legal" in warning_sections:
        recommendations.append("Increase legal text box height or reduce legal copy.")
    if "cta" in critical_sections or ("cta" in warning_sections and code in {"pt", "fr", "es"}):
        recommendations.append(f"Review CTA copy for {label} expansion.")
    if "price_offer" in critical_sections:
        recommendations.append("Consider alternate layout for high-expansion promotional copy.")
    if code in {"ja", "ko", "zh"} and not critical_sections:
        recommendations.append("CJK text compression likely fits comfortably.")
    if any(data.get("layout_risk") == "high" for data in sections.values()):
        recommendations.append("Consider alternate layout for high-expansion languages.")
    if not recommendations and critical_sections:
        recommendations.append(f"Review {label} copyfit before production.")
    return list(dict.fromkeys(recommendations))[:4]


def _reading(summary: dict[str, Any]) -> str:
    status = summary.get("overall_status", "unknown")
    worst = summary.get("worst_language")
    max_expansion = summary.get("max_expansion_pct", 0)
    sections = summary.get("primary_risk_sections", [])
    if status == "unknown":
        return ""
    risk_text = f" Primary risk sections: {', '.join(sections)}." if sections else ""
    return (
        f"Global Brand Guard fit simulation is {status}. Worst language is {worst or 'n/a'} "
        f"at {max_expansion:.1f}% estimated expansion.{risk_text}"
    )


def compute_linguistic_stress(
    text_blocks: list[dict[str, Any]],
    layout_analysis: dict[str, Any] | None = None,
    baseline_language: str = "en",
) -> dict[str, Any]:
    try:
        safe_blocks = text_blocks if isinstance(text_blocks, list) else []
        if not any(_block_text(block) for block in safe_blocks if isinstance(block, dict)):
            return _safe_empty(baseline_language)

        sections = _build_sections(safe_blocks, layout_analysis)
        total_chars = sum(section["chars"] for section in sections.values())
        if total_chars <= 0:
            return _safe_empty(baseline_language)

        constraints = _layout_section_constraints(_layout_blocks(layout_analysis))
        baseline = {"total_chars": total_chars, "sections": sections}
        languages: list[dict[str, Any]] = []
        critical_languages: list[str] = []
        warning_languages: list[str] = []
        comfortable_languages: list[str] = []
        primary_sections: set[str] = set()
        worst_language: str | None = None
        max_expansion_pct = 0.0

        for language in TARGET_LANGUAGES:
            code = language["code"]
            section_results: dict[str, dict[str, Any]] = {}
            weighted_estimated = 0.0
            weighted_baseline = 0.0
            language_has_critical = False
            language_has_warning = False
            for section, data in sections.items():
                baseline_text = data["text"]
                baseline_chars = int(data["chars"])
                factor = _section_factor(code, section, baseline_text) if baseline_chars else 1.0
                estimated_chars = int(math.ceil(baseline_chars * factor)) if baseline_chars else 0
                expansion_pct = round((estimated_chars / baseline_chars) * 100, 1) if baseline_chars else 0.0
                status = _status(expansion_pct) if baseline_chars else "ok"
                layout_risk = _layout_risk(section, expansion_pct, constraints) if baseline_chars else "low"
                if status == "critical":
                    language_has_critical = True
                    primary_sections.add(section)
                elif status == "warning":
                    language_has_warning = True
                    primary_sections.add(section)
                weighted_estimated += estimated_chars * float(data["weight"])
                weighted_baseline += baseline_chars * float(data["weight"])
                section_results[section] = {
                    "baseline_text": baseline_text,
                    "estimated_text": _estimated_text(baseline_text, estimated_chars),
                    "baseline_chars": baseline_chars,
                    "estimated_chars": estimated_chars,
                    "expansion_pct": expansion_pct,
                    "status": status,
                    "layout_risk": layout_risk,
                }

            score = weighted_estimated / max(1.0, weighted_baseline)
            expansion_pct = round(score * 100, 1)
            language_status = "critical" if language_has_critical or expansion_pct > 120 else "warning" if language_has_warning or expansion_pct > 100 else "ok"
            if language_status == "critical":
                critical_languages.append(code)
            elif language_status == "warning":
                warning_languages.append(code)
            else:
                comfortable_languages.append(code)
            if expansion_pct > max_expansion_pct:
                max_expansion_pct = expansion_pct
                worst_language = code
            language_result = {
                "code": code,
                "label": language["label"],
                "expansion_pct": expansion_pct,
                "status": language_status,
                "score": round(score, 3),
                "risk_level": _risk_level(language_status),
                "sections": section_results,
                "recommendations": _recommendations(code, language["label"], section_results),
            }
            languages.append(language_result)

        overall_status = "red" if critical_languages else "amber" if warning_languages else "green"
        summary = {
            "overall_status": overall_status,
            "critical_languages": critical_languages,
            "warning_languages": warning_languages,
            "comfortable_languages": comfortable_languages,
            "worst_language": worst_language,
            "max_expansion_pct": round(max_expansion_pct, 1),
            "primary_risk_sections": sorted(primary_sections, key=lambda section: SECTIONS.index(section)),
        }
        return {
            "version": 1,
            "baseline_language": baseline_language,
            "baseline": baseline,
            "languages": languages,
            "summary": summary,
            "reading": _reading(summary),
        }
    except Exception:
        return _safe_empty(baseline_language)
