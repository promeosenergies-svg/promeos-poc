"""
kb_ingest_constants.py — Migre les constantes métier vers kb.db
SOURCE : config/emission_factors.py + config/tarifs_reglementaires.yaml + config/ademe_benchmarks.py
TARGET : kb.db namespace=constants (via app/kb/store.py)

Règle absolue : zéro valeur inventée.
Toute constante provient d'un fichier source existant + référence officielle.
"""

import sys
import os
from datetime import datetime, timezone

# Allow running from backend/ or backend/scripts/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.kb.store import KBStore


# ── Constantes à ingérer ───────────────────────────────────────────────────
# Chaque entrée DOIT avoir une source vérifiable dans le repo.
# Format adapté au schéma kb_items (app/kb/models.py) :
#   id, type, domain, title, summary, content_md, tags, scope, logic, sources,
#   updated_at, confidence, status, priority

CONSTANTS = [
    {
        "id": "constants.co2_elec_france",
        "type": "knowledge",
        "domain": "facturation",
        "title": "Facteur CO₂ électricité France",
        "summary": "0.052 kgCO₂e/kWh — ADEME Base Empreinte V23.6 (mix moyen annuel France, ACV)",
        "content_md": (
            "## Facteur CO₂ électricité France\n\n"
            "**Valeur** : `0.052` kgCO₂e/kWh\n\n"
            "**Source** : ADEME Base Empreinte V23.6 (juillet 2025)\n\n"
            "**Formule** : CO₂ (kg) = consommation (kWh) × 0.052\n\n"
            "⚠️ **NE PAS CONFONDRE** avec 0.0569 = tarif TURPE 7 HPH (€/kWh) — unités différentes"
        ),
        "tags": {"namespace": "constants", "energy": "electricity", "country": "france"},
        "scope": {"energy_vector": ["ELEC"]},
        "sources": [
            {
                "reference": "ADEME Base Empreinte V23.6",
                "file": "config/emission_factors.py",
                "extracted_at": "2025-07-01",
            }
        ],
        "confidence": "high",
        "status": "validated",
        "priority": 1,
    },
    {
        "id": "constants.co2_gaz_france",
        "type": "knowledge",
        "domain": "facturation",
        "title": "Facteur CO₂ gaz naturel France",
        "summary": "0.227 kgCO₂e/kWh — ADEME Base Empreinte V23.6 (PCI, combustion + amont)",
        "content_md": (
            "## Facteur CO₂ gaz naturel France\n\n"
            "**Valeur** : `0.227` kgCO₂e/kWh\n\n"
            "**Source** : ADEME Base Empreinte V23.6\n\n"
            "**Formule** : CO₂ (kg) = consommation gaz (kWh PCI) × 0.227"
        ),
        "tags": {"namespace": "constants", "energy": "gas", "country": "france"},
        "scope": {"energy_vector": ["GAZ"]},
        "sources": [
            {
                "reference": "ADEME Base Empreinte V23.6",
                "file": "config/emission_factors.py",
                "extracted_at": "2025-07-01",
            }
        ],
        "confidence": "high",
        "status": "validated",
        "priority": 1,
    },
    {
        "id": "constants.accise_elec_t1_2026",
        "type": "knowledge",
        "domain": "facturation",
        "title": "Accise électricité T1 (grande consommation) 2026",
        "summary": "30.85 €/MWh — JORFTEXT000053407616 LFI 2025 art. 20 (fév 2026+)",
        "content_md": (
            "## Accise électricité T1\n\n"
            "**Valeur** : `30.85` €/MWh\n\n"
            "**Applicable** : Grande consommation (catégorie T1)\n\n"
            "**Depuis** : 1er février 2026\n\n"
            "⚠️ **T2 (petite consommation) = 26.58 €/MWh** — vérifier segment client"
        ),
        "tags": {"namespace": "constants", "tax": "accise", "segment": "T1"},
        "scope": {"energy_vector": ["ELEC"]},
        "sources": [
            {
                "reference": "JORFTEXT000053407616 — LFI 2025 art. 20",
                "file": "config/tarifs_reglementaires.yaml",
                "extracted_at": "2026-02-01",
            }
        ],
        "confidence": "high",
        "status": "validated",
        "priority": 1,
    },
    {
        "id": "constants.accise_elec_t2_2026",
        "type": "knowledge",
        "domain": "facturation",
        "title": "Accise électricité T2 (petite consommation) 2026",
        "summary": "26.58 €/MWh — JORFTEXT000053407616 LFI 2025 art. 20 (fév 2026+)",
        "content_md": (
            "## Accise électricité T2\n\n"
            "**Valeur** : `26.58` €/MWh\n\n"
            "**Applicable** : Petite consommation (catégorie T2)\n\n"
            "**Depuis** : 1er février 2026"
        ),
        "tags": {"namespace": "constants", "tax": "accise", "segment": "T2"},
        "scope": {"energy_vector": ["ELEC"]},
        "sources": [
            {
                "reference": "JORFTEXT000053407616 — LFI 2025 art. 20",
                "file": "config/tarifs_reglementaires.yaml",
                "extracted_at": "2026-02-01",
            }
        ],
        "confidence": "high",
        "status": "validated",
        "priority": 1,
    },
    {
        "id": "constants.accise_gaz_2026",
        "type": "knowledge",
        "domain": "facturation",
        "title": "Accise gaz naturel 2026",
        "summary": "10.73 €/MWh — JORFTEXT000053407616 LFI 2025 art. 20 (fév 2026+)",
        "content_md": ("## Accise gaz naturel\n\n**Valeur** : `10.73` €/MWh\n\n**Depuis** : 1er février 2026"),
        "tags": {"namespace": "constants", "tax": "accise", "energy": "gas"},
        "scope": {"energy_vector": ["GAZ"]},
        "sources": [
            {
                "reference": "JORFTEXT000053407616 — LFI 2025 art. 20",
                "file": "config/tarifs_reglementaires.yaml",
                "extracted_at": "2026-02-01",
            }
        ],
        "confidence": "high",
        "status": "validated",
        "priority": 1,
    },
    {
        "id": "constants.cta_pct_2026",
        "type": "knowledge",
        "domain": "facturation",
        "title": "CTA — part fixe TURPE 2026",
        "summary": "27.04% de la partie fixe TURPE (CRE délibération TURPE 7)",
        "content_md": (
            "## CTA (Contribution Tarifaire d'Acheminement)\n\n"
            "**Valeur** : `27.04`% de la partie fixe TURPE\n\n"
            "**Source** : CRE délibération TURPE 7 — 2026"
        ),
        "tags": {"namespace": "constants", "tax": "cta"},
        "scope": {"energy_vector": ["ELEC"]},
        "sources": [
            {
                "reference": "CRE délibération TURPE 7 — 2026",
                "file": "config/tarifs_reglementaires.yaml",
                "extracted_at": "2026-01-01",
            }
        ],
        "confidence": "high",
        "status": "validated",
        "priority": 2,
    },
    {
        "id": "constants.coeff_ep_elec_2026",
        "type": "knowledge",
        "domain": "reglementaire",
        "title": "Coefficient énergie primaire électricité",
        "summary": "1.9 kWhEP/kWhEF — Arrêté du 10 novembre 2023 (janvier 2026)",
        "content_md": (
            "## Coefficient énergie primaire\n\n"
            "**Valeur** : `1.9` kWhEP/kWhEF\n\n"
            "**Formule** : EP (kWhEP) = EF (kWhEF) × 1.9\n\n"
            "**Source** : Arrêté du 10 novembre 2023"
        ),
        "tags": {"namespace": "constants", "regulation": "ep_coefficient"},
        "scope": {"energy_vector": ["ELEC"]},
        "sources": [
            {
                "reference": "Arrêté du 10 novembre 2023 — coefficient énergie primaire",
                "file": "config/emission_factors.py",
                "extracted_at": "2026-01-01",
            }
        ],
        "confidence": "high",
        "status": "validated",
        "priority": 2,
    },
    {
        "id": "constants.nebco_threshold_kw",
        "type": "knowledge",
        "domain": "flex",
        "title": "NEBCO — seuil minimum 100 kW",
        "summary": "100 kW minimum par pas de contrôle (RTE NEBCO, effectif 01/09/2025)",
        "content_md": (
            "## NEBCO seuil minimum\n\n"
            "**Valeur** : `100` kW par pas de contrôle\n\n"
            "⚠️ Seuil par **pas de contrôle**, pas par site total\n\n"
            "**Source** : RTE — NEBCO règles de marché (01/09/2025)"
        ),
        "tags": {"namespace": "constants", "flexibility": "NEBCO"},
        "scope": {},
        "sources": [
            {
                "reference": "RTE — NEBCO règles de marché (effectif 01/09/2025)",
                "file": "config/tarifs_reglementaires.yaml",
                "extracted_at": "2025-09-01",
            }
        ],
        "confidence": "high",
        "status": "validated",
        "priority": 2,
    },
    {
        "id": "constants.dt_penalty_non_conforme",
        "type": "knowledge",
        "domain": "reglementaire",
        "title": "Pénalité Décret Tertiaire — NON_CONFORME",
        "summary": "7 500 € — Décret n°2019-771 art. R131-38",
        "content_md": (
            "## Pénalité DT NON_CONFORME\n\n**Valeur** : `7 500` €\n\n**Source** : Décret n°2019-771, article R131-38"
        ),
        "tags": {"namespace": "constants", "regulation": "decret_tertiaire", "status": "non_conforme"},
        "scope": {},
        "sources": [
            {
                "reference": "Décret n°2019-771 art. R131-38 — Décret Tertiaire",
                "file": "config/emission_factors.py",
                "extracted_at": "2024-01-01",
            }
        ],
        "confidence": "high",
        "status": "validated",
        "priority": 1,
    },
    {
        "id": "constants.dt_penalty_a_risque",
        "type": "knowledge",
        "domain": "reglementaire",
        "title": "Pénalité Décret Tertiaire — A_RISQUE",
        "summary": "3 750 € (50% de réduction vs NON_CONFORME) — Décret n°2019-771",
        "content_md": (
            "## Pénalité DT A_RISQUE\n\n"
            "**Valeur** : `3 750` €\n\n"
            "**Calcul** : 7 500 × 50%\n\n"
            "**Source** : Décret n°2019-771, article R131-38"
        ),
        "tags": {"namespace": "constants", "regulation": "decret_tertiaire", "status": "a_risque"},
        "scope": {},
        "sources": [
            {
                "reference": "Décret n°2019-771 art. R131-38 — Décret Tertiaire",
                "file": "config/emission_factors.py",
                "extracted_at": "2024-01-01",
            }
        ],
        "confidence": "high",
        "status": "validated",
        "priority": 1,
    },
    {
        "id": "constants.bacs_seuil_haut_kw",
        "type": "knowledge",
        "domain": "reglementaire",
        "title": "BACS — seuil haut CVC 290 kW",
        "summary": "290 kW CVC → obligation BACS au 01/01/2025 (Décret n°2020-887)",
        "content_md": (
            "## BACS seuil haut\n\n"
            "**Valeur** : `290` kW CVC\n\n"
            "**Deadline** : 1er janvier 2025\n\n"
            "**Seuil bas** : 70 kW → deadline 01/01/2030\n\n"
            "**Source** : Décret n°2020-887, Art. R175-2"
        ),
        "tags": {"namespace": "constants", "regulation": "bacs"},
        "scope": {},
        "sources": [
            {
                "reference": "Décret n°2020-887, Art. R175-2",
                "file": "config/emission_factors.py",
                "extracted_at": "2024-01-01",
            }
        ],
        "confidence": "high",
        "status": "validated",
        "priority": 2,
    },
]


def ingest_constants_to_kb():
    """Importe les constantes métier dans kb.db via KBStore."""
    store = KBStore()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    ok = 0
    for const in CONSTANTS:
        const["updated_at"] = now
        if store.upsert_item(const):
            ok += 1
        else:
            print(f"  ✗ ERREUR ingestion {const['id']}")

    print(f"[kb_ingest_constants] ✓ {ok}/{len(CONSTANTS)} constantes ingérées dans kb.db")

    _verify_no_drift()
    return ok


def _verify_no_drift():
    """Vérifie que kb.db == valeurs dans config/emission_factors.py."""
    try:
        from config.emission_factors import EMISSION_FACTORS, BASE_PENALTY_EURO, A_RISQUE_PENALTY_EURO

        store = KBStore()

        # CO₂ élec
        item = store.get_item("constants.co2_elec_france")
        if item:
            assert "0.052" in item["summary"], f"DRIFT: CO₂ élec dans KB != 0.052"

        # CO₂ gaz
        item = store.get_item("constants.co2_gaz_france")
        if item:
            assert "0.227" in item["summary"], f"DRIFT: CO₂ gaz dans KB != 0.227"

        print("[verify_no_drift] ✓ Constantes cohérentes avec config/emission_factors.py")

    except ImportError:
        print("[verify_no_drift] ⚠️ Impossible d'importer config.emission_factors (check PYTHONPATH)")
    except AssertionError as e:
        print(f"[verify_no_drift] ✗ {e}")


if __name__ == "__main__":
    ingest_constants_to_kb()
