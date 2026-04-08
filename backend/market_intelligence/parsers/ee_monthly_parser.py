"""
Parser pour mensuels EuropEnergies (N281, N282, N283).
20 pages. Extrait : édito, indicateurs spot, page marchés, articles.
"""

import re
from pathlib import Path
from datetime import datetime, timezone

from models.enums import ArticleCategory, ArticleSource
from .base_parser import (
    extract_text_pdftotext,
    get_page_count,
    parse_monthly_date,
    parse_fr_number,
    compute_content_hash,
    auto_tag,
)


def parse_monthly_pdf(pdf_path: str) -> dict:
    """Parse un mensuel complet. Retourne {"articles": [...], "indicators": [...]}."""
    path = Path(pdf_path)
    full_text = extract_text_pdftotext(pdf_path)
    if not full_text.strip():
        return {"articles": [], "indicators": []}

    parsed = parse_monthly_date(full_text[:300])
    if not parsed:
        return {"articles": [], "indicators": []}
    issue, source_date = parsed

    articles = []
    indicators = []

    # 1. Indicateurs spot (page 1)
    page1_text = extract_text_pdftotext(pdf_path, first_page=1, last_page=1)
    spot_indicators = _extract_spot_indicators(page1_text, path.name, issue, source_date)
    indicators.extend(spot_indicators)

    # 2. Édito (page 1)
    edito = _extract_edito(page1_text, path.name, issue, source_date)
    if edito:
        articles.append(edito)

    # 3. Page marchés (dernières pages)
    page_count = get_page_count(pdf_path)
    market_text = extract_text_pdftotext(pdf_path, first_page=max(1, page_count - 1), last_page=page_count)
    market_indicators = _extract_market_page_indicators(market_text, path.name, issue, source_date)
    indicators.extend(market_indicators)

    if market_text and len(market_text) > 100:
        tags = auto_tag(market_text)
        articles.append(
            {
                "source": ArticleSource.EUROP_ENERGIES,
                "category": ArticleCategory.MARKET_REVIEW,
                "title": f"Les marchés – {issue}",
                "body_text": market_text,
                "summary": market_text[:300].rsplit(".", 1)[0] + "." if "." in market_text[:300] else market_text[:300],
                "countries": tags["countries"],
                "topics": tags["topics"],
                "entities": tags["entities"],
                "energy_types": tags["energy_types"],
                "source_file": path.name,
                "source_date": source_date,
                "source_issue": issue,
                "content_hash": compute_content_hash(f"Marchés {issue}", market_text, source_date.isoformat()),
                "promeos_relevance": 0.95,
                "promeos_modules": ["achat", "executive"],
            }
        )

    return {"articles": articles, "indicators": indicators}


def _extract_spot_indicators(page1_text: str, source_file: str, issue: str, source_date: datetime) -> list[dict]:
    """Extrait les indicateurs spot du tableau page 1."""
    indicators = []
    lines = page1_text.split("\n")
    current_category = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if "lectricit" in line:
            current_category = "ELEC"
            continue
        elif "Gaz" in line and ("MWh" in line or "mwh" in line.lower()):
            current_category = "GAZ"
            continue
        elif "trole" in line or "Pétrole" in line:
            current_category = "PETROLE"
            continue
        elif "CO2" in line or "CO₂" in line:
            current_category = "CO2"
            continue

        if current_category is None:
            continue

        m = re.match(
            r"(\w[\w\s/()€$*]*?)\s{2,}([\d,.\-+]+)\s+([\d,.\-+]+)\s+([\d,.\-+]+)",
            line,
        )
        if not m:
            continue

        name_raw = m.group(1).strip()
        val_curr = parse_fr_number(m.group(3))
        variation = parse_fr_number(m.group(4))

        indicator_name = _map_indicator_name(name_raw, current_category)
        if not indicator_name:
            continue

        unit = "EUR_MWH"
        if current_category == "PETROLE":
            unit = "USD_BBL"
        elif current_category == "CO2":
            unit = "EUR_T"

        indicators.append(
            {
                "indicator_name": indicator_name,
                "period_label": source_date.strftime("%Y-%m"),
                "period_start": source_date,
                "value_eur_mwh": val_curr,
                "variation_pct": variation,
                "unit": unit,
                "source_file": source_file,
                "source_issue": issue,
            }
        )

    return indicators


def _extract_market_page_indicators(
    market_text: str, source_file: str, issue: str, source_date: datetime
) -> list[dict]:
    """Extrait les données de la page marchés (forwards OTC, DA averages)."""
    indicators = []

    forward_pattern = re.compile(
        r"((?:Janvier|F.vrier|Mars|Avril|Mai|Juin|Juillet|Ao.t|Septembre|Octobre|Novembre|D.cembre|"
        r"T[1-4]|Cal-?\d{2})\s*\d{0,4})\s+"
        r"([\d,]+)\s+([\d,]+)\s+([\d,]+)"
    )

    for m in forward_pattern.finditer(market_text):
        label = m.group(1).strip()
        val_low = parse_fr_number(m.group(2))
        val_high = parse_fr_number(m.group(3))
        val_close = parse_fr_number(m.group(4))

        indicators.append(
            {
                "indicator_name": f"FORWARD_BASELOAD_FR_{label.replace(' ', '_')}",
                "period_label": label,
                "period_start": source_date,
                "value_eur_mwh": val_close,
                "value_low": val_low,
                "value_high": val_high,
                "value_close": val_close,
                "unit": "EUR_MWH",
                "source_file": source_file,
                "source_issue": issue,
            }
        )

    return indicators


def _extract_edito(page1_text: str, source_file: str, issue: str, source_date: datetime) -> dict | None:
    """Extrait l'édito de la page 1."""
    m = re.search(r"[EÉ]dito\s*(.*)", page1_text, re.DOTALL)
    if not m:
        return None
    edito_text = m.group(1).strip()
    if len(edito_text) < 100:
        return None

    tags = auto_tag(edito_text)
    return {
        "source": ArticleSource.EUROP_ENERGIES,
        "category": ArticleCategory.EDITORIAL,
        "title": f"Édito – {issue}",
        "body_text": edito_text,
        "summary": edito_text[:300].rsplit(".", 1)[0] + "." if "." in edito_text[:300] else edito_text[:300],
        "countries": tags["countries"],
        "topics": tags["topics"],
        "entities": tags["entities"],
        "energy_types": tags["energy_types"],
        "source_file": source_file,
        "source_date": source_date,
        "source_issue": issue,
        "content_hash": compute_content_hash(f"Edito {issue}", edito_text, source_date.isoformat()),
        "promeos_relevance": tags["promeos_relevance"],
        "promeos_modules": tags["promeos_modules"],
    }


def _map_indicator_name(raw: str, category: str) -> str | None:
    """Mappe un nom brut vers un indicator_name canonical."""
    mapping = {
        ("France", "ELEC"): "SPOT_DA_BASE_FR",
        ("Allemagne", "ELEC"): "SPOT_DA_BASE_DE",
        ("Belgique", "ELEC"): "SPOT_DA_BASE_BE",
        ("TRF", "GAZ"): "GAZ_TRF",
        ("TTF", "GAZ"): "GAZ_TTF",
        ("Brent", "PETROLE"): "BRENT",
        ("WTI", "PETROLE"): "WTI",
        ("EUA", "CO2"): "EUA",
    }
    for (name_key, cat_key), indicator in mapping.items():
        if name_key.lower() in raw.lower() and cat_key == category:
            return indicator
    return None
