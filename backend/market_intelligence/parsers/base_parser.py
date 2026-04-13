"""
Base parser pour documents EuropEnergies.
Pattern: extract_text → split_articles → tag → hash → return structured dicts.
"""

import re
import subprocess
from hashlib import sha256
from datetime import datetime, timezone
from typing import Optional


def extract_text_pdftotext(pdf_path: str, first_page: int = 1, last_page: int = 0) -> str:
    """Extraction texte via pdftotext (meilleur pour les PDFs multi-colonnes)."""
    cmd = ["pdftotext", "-layout"]
    if last_page > 0:
        cmd += ["-f", str(first_page), "-l", str(last_page)]
    cmd += [pdf_path, "-"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return result.stdout


def extract_text_pypdf(pdf_path: str) -> str:
    """Fallback extraction via pypdf."""
    from pypdf import PdfReader

    reader = PdfReader(pdf_path)
    return "\n\n".join(page.extract_text() or "" for page in reader.pages)


def get_page_count(pdf_path: str) -> int:
    """Get PDF page count via pdfinfo (poppler-utils). Fallback to pypdf if absent."""
    try:
        result = subprocess.run(
            ["pdfinfo", pdf_path], capture_output=True, text=True, timeout=10
        )
        for line in result.stdout.splitlines():
            if line.startswith("Pages:"):
                return int(line.split(":", 1)[1].strip())
    except (FileNotFoundError, subprocess.SubprocessError, ValueError):
        pass
    from pypdf import PdfReader

    return len(PdfReader(pdf_path).pages)


def compute_content_hash(title: str, body: str, source_date: str) -> str:
    """Hash déterministe pour déduplication idempotente."""
    content = f"{title}|{body[:500]}|{source_date}"
    return sha256(content.encode("utf-8")).hexdigest()


def parse_ee_date(text: str) -> Optional[datetime]:
    """
    Parse les dates EuropEnergies :
    - "Flashes – 8.04.26" → datetime(2026, 4, 8)
    - "Gros plan – 8.04.26" → datetime(2026, 4, 8)
    """
    m = re.search(r"(\d{1,2})\.(\d{2})\.(\d{2})", text)
    if m:
        day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        full_year = 2000 + year if year < 100 else year
        return datetime(full_year, month, day, tzinfo=timezone.utc)
    return None


def parse_monthly_date(text: str) -> Optional[tuple[str, datetime]]:
    """
    Parse l'en-tête mensuel : "24e année - N° 283 - mars 2026"
    Retourne (issue_number, date_premier_du_mois)
    """
    m = re.search(r"N[°o]\s*(\d+)\s*-\s*(\w+)\s+(\d{4})", text)
    if not m:
        return None
    issue = f"N{m.group(1)}"
    month_name = m.group(2).lower()
    year = int(m.group(3))
    months_fr = {
        "janvier": 1,
        "fevrier": 2,
        "février": 2,
        "mars": 3,
        "avril": 4,
        "mai": 5,
        "juin": 6,
        "juillet": 7,
        "aout": 8,
        "août": 8,
        "septembre": 9,
        "octobre": 10,
        "novembre": 11,
        "decembre": 12,
        "décembre": 12,
    }
    month_num = months_fr.get(month_name, 1)
    return issue, datetime(year, month_num, 1, tzinfo=timezone.utc)


def parse_fr_number(s: str) -> Optional[float]:
    """Parse un nombre français : '46,02' → 46.02, '-54,63' → -54.63"""
    try:
        return float(s.replace(",", ".").replace(" ", "").replace("+", ""))
    except (ValueError, AttributeError):
        return None


# ── Tagging automatique par keywords ──

COUNTRY_KEYWORDS = {
    "FR": ["France", "français", "française", "CRE", "RTE", "Enedis", "EDF", "ADEME"],
    "DE": ["Allemagne", "allemand", "EEX", "Bundesnetzagentur"],
    "BE": ["Belgique", "belge", "Creg", "Brugel", "Fluxys"],
    "NL": ["Pays-Bas", "néerlandais", "Frank Énergie"],
    "ES": ["Espagne", "espagnol"],
    "IT": ["Italie", "italien"],
    "EU": ["européen", "Commission européenne", "UE", "Bruxelles", "ENTSO"],
    "UK": ["Royaume-Uni", "britannique", "Octopus"],
    "US": ["États-Unis", "américain", "Trump", "Washington"],
}

TOPIC_KEYWORDS = {
    "spot": ["spot", "day-ahead", "EPEX", "prix horaire"],
    "forward": ["forward", "terme", "Cal-2", "Cal-27", "CAL", "OTC"],
    "nuclear": ["nucléaire", "EPR", "réacteur", "Flamanville", "Gravelines"],
    "ENR": ["renouvelable", "éolien", "solaire", "photovoltaïque", "PV", "EnR"],
    "VNU": ["VNU", "ARENH", "post-ARENH", "versement nucléaire"],
    "GO": ["garantie d'origine", "enchères GO", "AIB"],
    "PPA": ["PPA", "CPPA", "power purchase", "contrat long terme"],
    "gas": ["gaz", "TTF", "TRF", "GNL", "LNG", "Ormuz"],
    "oil": ["pétrole", "Brent", "WTI", "raffinerie", "baril"],
    "CO2": ["CO2", "EUA", "carbone", "quota", "ETS"],
    "capacity": ["capacité", "MECAPA", "enchère de capacité"],
    "flex": ["flexibilité", "effacement", "NEBEF", "NEBCO", "stockage", "batterie", "BESS"],
    "tariff": ["TURPE", "CSPE", "accise", "CTA", "tarif"],
    "DT": ["décret tertiaire", "OPERAT", "rénovation tertiaire"],
    "grid": ["réseau", "raccordement", "transport"],
    "geopolitics": ["guerre", "Iran", "Israël", "Ormuz", "crise", "géopolitique"],
    "autoconsommation": ["autoconsommation", "collective", "MWc"],
}

ENTITY_PATTERNS = [
    "EDF",
    "Engie",
    "TotalEnergies",
    "RTE",
    "Enedis",
    "CRE",
    "ADEME",
    "Alterna",
    "Octopus",
    "Vattenfall",
    "Neoen",
    "Iberdrola",
    "Naturgy",
    "GazelEnergie",
    "Ekwateur",
    "QatarEnergy",
    "Bamboo Energy",
    "CVE",
    "Commission européenne",
    "Conseil d'État",
    "GRDF",
    "Storengy",
    "Teréga",
]

PROMEOS_MODULE_MAP = {
    "achat": ["spot", "forward", "PPA", "VNU", "GO", "capacity"],
    "billing": ["tariff"],
    "conformite": ["DT"],
    "flex": ["flex", "capacity"],
    "conso": ["ENR", "autoconsommation", "grid"],
    "executive": ["geopolitics", "oil", "gas", "CO2"],
}


def auto_tag(text: str) -> dict:
    """Tagging automatique par détection de keywords dans le texte."""
    text_lower = text.lower()
    countries = [code for code, kws in COUNTRY_KEYWORDS.items() if any(kw.lower() in text_lower for kw in kws)]
    topics = [topic for topic, kws in TOPIC_KEYWORDS.items() if any(kw.lower() in text_lower for kw in kws)]
    entities = [e for e in ENTITY_PATTERNS if e.lower() in text_lower]
    energy_types = []
    if any(t in topics for t in ["spot", "forward", "nuclear", "ENR", "tariff", "capacity", "flex"]):
        energy_types.append("ELEC")
    if any(t in topics for t in ["gas"]):
        energy_types.append("GAZ")
    if any(t in topics for t in ["oil"]):
        energy_types.append("PETROLE")

    promeos_topics = ["spot", "forward", "VNU", "tariff", "DT", "flex", "GO", "PPA", "capacity"]
    relevance = min(1.0, sum(0.15 for t in topics if t in promeos_topics))
    relevance = max(0.2, relevance)

    modules = list(set(mod for mod, mod_topics in PROMEOS_MODULE_MAP.items() if any(t in topics for t in mod_topics)))

    return {
        "countries": countries or ["FR"],
        "topics": topics,
        "entities": entities,
        "energy_types": energy_types or ["ELEC"],
        "promeos_relevance": round(relevance, 2),
        "promeos_modules": modules or ["executive"],
    }
