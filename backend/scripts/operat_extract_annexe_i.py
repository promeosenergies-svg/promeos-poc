"""
Parser deterministe pour Annexe I de l'arrete OPERAT NOR ATDL2430864A (01/08/2025).

Extrait depuis docs/sources/regulatory/operat/atdl2430864a_annexe_i.txt :
- Liste des 60 categories d'activites
- Pour chaque sous-categorie : NAF, CVC × (8 zones + 5 DOM) × 5 paliers altitude,
  USE etalon, Part_USE_variable, IIU temporels/surfaciques, formule modulation, notas.

Sortie : backend/config/operat_annexe_i_sous_categories.json (donnees brutes structurees).

Usage : /Users/amine/projects/promeos-poc/backend/venv/bin/python backend/scripts/operat_extract_annexe_i.py
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "docs/sources/regulatory/operat/atdl2430864a_annexe_i.txt"
OUT = ROOT / "backend/config/operat_annexe_i_sous_categories.json"

ZONES = [
    "H1a",
    "H1b",
    "H1c",
    "H2a",
    "H2b",
    "H2c",
    "H2d",
    "H3",
    "Guadeloupe",
    "Martinique",
    "Guyane",
    "Reunion",
    "Mayotte",
]

PALIERS = [
    ("alt_lt_400", "Altitude < 400 m"),
    ("alt_400_800", "400 m"),  # "400 m ≤ Altitude < 800 m"
    ("alt_800_1200", "800 m"),
    ("alt_1200_1600", "1200 m"),
    ("alt_gte_1600", "Altitude ≥ 1600 m"),
]

# Patterns
# Le PDF rend les titres en « Sous-categorie "..." » mais parfois le » final est absent
# (cf. cat. Sport ligne 51897). De plus, certaines sous-cat. de Sport utilisent U+201C
# en ouverture ET fermeture (glitch rendu PDF). On accepte tous les guillemets typo
# en ouverture et en fermeture pour robustesse.
QUOTE_CLASS = r'["“”]'
SUBCAT_TITLE_RE = re.compile(rf"«\s*Sous-cat[ée]gorie\s+{QUOTE_CLASS}([^“”\"]+?){QUOTE_CLASS}", re.MULTILINE)
NAF_RE = re.compile(r"\(\s*NAF\s*:\s*(.+?)\s*\)", re.DOTALL)
USE_ETALON_RE = re.compile(r"USE\s+[ée]talon\s*=\s*([\d.,\s]+?)\s*kWh/m[²2]/an", re.IGNORECASE)
PART_USE_RE = re.compile(r"Part_USE_variable\s*=\s*([\d.,]+)", re.IGNORECASE)
CATEGORY_HEADER_RE = re.compile(r"^\s*(\d+)\)\s*$", re.MULTILINE)

PALIER_PATTERNS = [
    (re.compile(r"^Altitude\s*<\s*400\s*m"), "alt_lt_400", "<400m"),
    (re.compile(r"^400\s*m\s*[≤<=]+\s*Altitude\s*<\s*800\s*m"), "alt_400_800", "[400-800)"),
    (re.compile(r"^800\s*m\s*[≤<=]+\s*Altitude\s*<\s*1200\s*m"), "alt_800_1200", "[800-1200)"),
    (re.compile(r"^1200\s*m\s*[≤<=]+\s*Altitude\s*<\s*1600\s*m"), "alt_1200_1600", "[1200-1600)"),
    (re.compile(r"^Altitude\s*[≥>=]+\s*1600\s*m"), "alt_gte_1600", ">=1600m"),
]


def normalize(text: str) -> str:
    """NFC + simplification accents specifiques."""
    return unicodedata.normalize("NFC", text)


def parse_number(line: str):
    """Convertit '57', '3 120', '0,77', '0,000247' en float/int. Vide -> None."""
    s = line.strip()
    if not s:
        return None
    s = s.replace(" ", " ").replace(" ", "")
    s = s.replace(",", ".")
    try:
        if "." in s:
            return float(s)
        return int(s)
    except ValueError:
        return None


def split_sub_categories(text: str) -> list[dict]:
    """Decoupe le texte en blocs sous-categorie."""
    matches = list(SUBCAT_TITLE_RE.finditer(text))
    blocks = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        title = m.group(1).strip()
        block_text = text[start:end]
        blocks.append({"title": title, "text": block_text, "start_offset": start})
    return blocks


def extract_naf(block_text: str) -> str | None:
    m = NAF_RE.search(block_text)
    if not m:
        return None
    return re.sub(r"\s+", " ", m.group(1)).strip()


def find_palier_for_line(line: str):
    s = line.strip()
    for rx, key, label in PALIER_PATTERNS:
        if rx.search(s):
            return key, label
    return None, None


def extract_cvc_table(block_text: str) -> dict:
    """Extrait les 5 paliers × 13 zones. Empty cell -> None."""
    lines = block_text.split("\n")

    # On localise la zone CVC : entre "Composante CVC" et "Composante USE"
    cvc_start_idx = None
    cvc_end_idx = None
    for i, ln in enumerate(lines):
        if "Composante CVC" in ln and cvc_start_idx is None:
            cvc_start_idx = i
        if "Composante USE" in ln and cvc_start_idx is not None:
            cvc_end_idx = i
            break
    if cvc_start_idx is None:
        return {}
    if cvc_end_idx is None:
        cvc_end_idx = len(lines)

    cvc_block = lines[cvc_start_idx:cvc_end_idx]

    # Strategy: scanner les lignes, detecter les en-tetes de palier (PALIER_PATTERNS).
    # Apres chaque palier, lire les 13 lignes suivantes (en sautant les lignes vides ?)
    # MAIS le PDF rend les cellules vides comme lignes blanches (positionnelles).
    # Donc il faut LIRE 13 lignes consecutives apres l'en-tete (compris les vides).

    paliers_data = {key: [None] * 13 for key, _ in PALIERS}

    i = 0
    while i < len(cvc_block):
        ln = cvc_block[i]
        # Detect palier header (peut etre en plusieurs lignes, cf "1200 m ≤ Altitude < 1600 m\n  Référence 1400 m")
        # On regarde si c'est un debut de palier avec sa reference, parfois sur 2 lignes
        palier_key, palier_label = find_palier_for_line(ln)
        if palier_key is None:
            i += 1
            continue

        # Determiner ou s'arrete l'en-tete de palier (incluant "Référence X m")
        # Le header occupe 1 ou 2 lignes selon le PDF.
        # On avance jusqu'a ce que la ligne suivante soit une donnee numerique (ou vide)
        # Heuristique : header se termine si "Référence" apparait dans la ligne courante OU suivante.
        header_lines = 1
        if "Référence" not in ln and i + 1 < len(cvc_block) and "Référence" in cvc_block[i + 1]:
            header_lines = 2

        # Lire 13 cellules a partir de i + header_lines
        start_idx = i + header_lines
        cells = []
        j = start_idx
        while len(cells) < 13 and j < len(cvc_block):
            cell_line = cvc_block[j]
            # Si on tombe sur un autre palier header avant d'avoir 13 cellules, on stoppe (cellules manquantes -> None)
            other_palier, _ = find_palier_for_line(cell_line)
            if other_palier is not None:
                # Stop here, fill remaining with None
                while len(cells) < 13:
                    cells.append(None)
                break
            # Si on tombe sur une autre section (Composante USE etc) -> stop
            if "Composante USE" in cell_line or cell_line.strip().startswith("«") or "USE étalon" in cell_line:
                while len(cells) < 13:
                    cells.append(None)
                break
            cells.append(parse_number(cell_line))
            j += 1

        paliers_data[palier_key] = cells
        i = j

    return paliers_data


def extract_use(block_text: str) -> dict:
    use_etalon = None
    part_use = None
    m = USE_ETALON_RE.search(block_text)
    if m:
        # USE etalon may span multiple lines, the regex captures with whitespace
        raw = m.group(1).strip()
        use_etalon = parse_number(raw)
    m2 = PART_USE_RE.search(block_text)
    if m2:
        part_use = parse_number(m2.group(1))
    return {"use_etalon_kwh_m2_an": use_etalon, "part_use_variable": part_use}


def extract_iiu_block(block_text: str) -> str:
    """Extrait le bloc IIU (Composante USE -> Formule de modulation)."""
    start = block_text.find("Composante USE")
    end = block_text.find("Formule de modulation")
    if start == -1:
        return ""
    if end == -1:
        end = len(block_text)
    return block_text[start:end].strip()


def extract_modulation_formula(block_text: str) -> str:
    """Extrait la formule de modulation."""
    m = re.search(
        r"Formule de modulation.*?(USE\s*modul[ée]\s*\(kWh/m[²2]/an\)\s*=.*?)(?:Nota|La valeur de|0,28xCVCx|\Z)",
        block_text,
        re.DOTALL | re.IGNORECASE,
    )
    if m:
        return re.sub(r"\s+", " ", m.group(1)).strip()
    return ""


def detect_categories(text: str) -> list[dict]:
    """Detecte les 60 categories listees pages 2-3 et leurs offsets dans la section III.

    Le sommaire est en pages 2-3 (lignes ~73-209). La section III commence apres
    'III. Valeurs absolues 2030' (ligne ~224). Chaque categorie est numerotee (1) à 60))
    suivie de son nom sur la ligne suivante.
    """
    # Trouver "III. Valeurs absolues 2030"
    iii_match = re.search(r"^III\.\s*Valeurs absolues 2030\s*$", text, re.MULTILINE)
    if not iii_match:
        return []
    section_iii_start = iii_match.end()
    section_text = text[section_iii_start:]

    # Pattern: ligne "X) " seule, suivie d'une ligne avec le nom de la categorie
    # Ex:  "1) \nAccueil petite enfance \n"
    cat_pattern = re.compile(r"^\s*(\d+)\)\s*$", re.MULTILINE)
    matches = list(cat_pattern.finditer(section_text))

    categories = []
    for idx, m in enumerate(matches):
        cat_num = int(m.group(1))
        # Ligne suivante = nom de la categorie
        after = section_text[m.end() :]
        # Premiere ligne non vide
        for line in after.split("\n")[1:6]:
            name = line.strip()
            if name and not name.startswith("•") and not name.startswith("I.") and not name.startswith("II."):
                next_offset = matches[idx + 1].start() if idx + 1 < len(matches) else len(section_text)
                categories.append(
                    {
                        "num": cat_num,
                        "name": name,
                        "offset_start_in_section_iii": m.start(),
                        "offset_end_in_section_iii": next_offset,
                        "offset_start_in_full_text": section_iii_start + m.start(),
                        "offset_end_in_full_text": section_iii_start + next_offset,
                    }
                )
                break
    return categories


def main():
    text = SRC.read_text(encoding="utf-8")
    text = normalize(text)

    # 1) Detecter les categories
    categories = detect_categories(text)
    print(f"Categories detectees: {len(categories)}")

    # 2) Pour chaque categorie, extraire ses sous-categories
    output = {
        "source": "docs/sources/regulatory/operat/atdl2430864a_annexe_i.pdf",
        "nor": "ATDL2430864A",
        "extraction_method": "PyMuPDF text + regex deterministe (backend/scripts/operat_extract_annexe_i.py)",
        "extraction_date": "2026-05-03",
        "zones_order": ZONES,
        "paliers_order": [k for k, _ in PALIERS],
        "categories_count": len(categories),
        "categories": [],
    }

    total_sub = 0
    for cat in categories:
        cat_text = text[cat["offset_start_in_full_text"] : cat["offset_end_in_full_text"]]
        sub_blocks = split_sub_categories(cat_text)
        sub_categories = []
        for sb in sub_blocks:
            naf = extract_naf(sb["text"])
            cvc = extract_cvc_table(sb["text"])
            use = extract_use(sb["text"])
            iiu = extract_iiu_block(sb["text"])
            formula = extract_modulation_formula(sb["text"])
            sub_categories.append(
                {
                    "title": sb["title"],
                    "naf": naf,
                    "cvc_kwh_m2_an": cvc,
                    "use_etalon_kwh_m2_an": use["use_etalon_kwh_m2_an"],
                    "part_use_variable": use["part_use_variable"],
                    "iiu_block_raw": iiu[:2000],  # Limite raison stockage
                    "modulation_formula": formula,
                }
            )
        total_sub += len(sub_categories)
        output["categories"].append(
            {
                "num": cat["num"],
                "name": cat["name"],
                "sub_categories": sub_categories,
                "sub_categories_count": len(sub_categories),
            }
        )

    output["total_sub_categories"] = total_sub
    print(f"Total sous-categories extraites: {total_sub}")

    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Output: {OUT}")
    print(f"Size: {OUT.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
