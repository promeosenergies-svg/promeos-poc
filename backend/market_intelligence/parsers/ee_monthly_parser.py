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
    """Extrait les indicateurs de la page marchés (spot moyens, TTF, Brent, Cal-X)."""
    # Normalise le texte : pdftotext -layout casse les phrases multi-colonnes
    market_text = re.sub(r"\s+", " ", market_text)
    indicators = []
    seen_names = set()

    def _push(name: str, value: float | None, variation: float | None, unit: str = "EUR_MWH", label: str | None = None):
        if value is None or name in seen_names:
            return
        seen_names.add(name)
        indicators.append(
            {
                "indicator_name": name,
                "period_label": label or source_date.strftime("%Y-%m"),
                "period_start": source_date,
                "value_eur_mwh": value,
                "variation_pct": variation,
                "unit": unit,
                "source_file": source_file,
                "source_issue": issue,
            }
        )

    # Spot électricité France (narratif) : "spot atteignant en moyenne 46,02 €/MWh, en baisse de 54 %"
    m = re.search(
        r"spot\s+atteignant\s+en\s+moyenne\s+([\d,]+)\s*€/MWh[^.]*?(hausse|baisse)\s+de\s+([\d,]+)",
        market_text,
        re.IGNORECASE,
    )
    if m:
        val = parse_fr_number(m.group(1))
        var = parse_fr_number(m.group(3))
        if val is not None and var is not None and m.group(2).lower() == "baisse":
            var = -var
        _push("SPOT_DA_BASE_FR", val, var)

    # Spot TTF : "TTF spot a terminé à 31,71 €/MWh... en baisse de 22 %"
    m = re.search(
        r"TTF\s+spot\s+a\s+termin.\s+.\s+([\d,]+)\s*€/\s*MWh[^.]*?(hausse|baisse)\s+de\s+([\d,]+)",
        market_text,
        re.IGNORECASE,
    )
    if m:
        val = parse_fr_number(m.group(1))
        var = parse_fr_number(m.group(3))
        if val is not None and var is not None and m.group(2).lower() == "baisse":
            var = -var
        _push("GAZ_TTF_SPOT", val, var)

    # Brent : "Brent dépasse les 110 euros/barils" ou "Brent a clôturé à 72,3 $/b"
    m = re.search(r"Brent[^.]*?([\d,]+)\s*(?:€|euros?|\$)?\s*/?\s*(?:b(?:aril)?s?)", market_text, re.IGNORECASE)
    if m:
        _push("BRENT", parse_fr_number(m.group(1)), None, unit="USD_BBL")

    # Forwards baseload FR : "Cal-27 ... à 50,04 €/MWh", "T2 a perdu 29 % à 21,54 €/MWh"
    for fm in re.finditer(
        r"Cal-?(\d{2})[^.]{0,200}?\b.?\s*([\d]{1,3}(?:,\d{1,2})?)\s*€/\s*MWh",
        market_text,
    ):
        period = fm.group(1)
        val = parse_fr_number(fm.group(2))
        _push(f"FORWARD_BASELOAD_FR_CAL_{period}", val, None, label=f"Cal-{period}")

    for fm in re.finditer(
        r"\bT([1-4])\b[^.]{0,200}?\b.?\s*([\d]{1,3}(?:,\d{1,2})?)\s*€/\s*MWh",
        market_text,
    ):
        period = fm.group(1)
        val = parse_fr_number(fm.group(2))
        _push(f"FORWARD_BASELOAD_FR_T{period}", val, None, label=f"T{period}")

    # "contrat mars a chuté ... à 41,82 €/MWh" → front-month
    m = re.search(
        r"contrat\s+(\w+)\s+a\s+(?:chut.|recul.|perdu|progress.|gagn.)[^.]{0,120}?\b([\d]{1,3}(?:,\d{1,2})?)\s*€/\s*MWh",
        market_text,
        re.IGNORECASE,
    )
    if m:
        _push(f"FRONT_MONTH_FR_{m.group(1).upper()}", parse_fr_number(m.group(2)), None, label=m.group(1))

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
