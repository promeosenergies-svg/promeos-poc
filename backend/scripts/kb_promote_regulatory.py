"""
PROMEOS KB - Promote key regulatory drafts to validated status.
Enriches tags, scope, and logic for the apply engine.

Usage: python backend/scripts/kb_promote_regulatory.py
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.kb.store import KBStore
from app.kb.indexer import KBIndexer

store = KBStore()
indexer = KBIndexer()


# ── BACS items to promote ───────────────────────────────────────────
BACS_PROMOTIONS = [
    {
        "id": "BACS_SEUILS_3",
        "confidence": "high",
        "tags": {
            "energy": ["elec", "gaz"],
            "segment": ["tertiaire_multisite", "collectivite"],
            "asset": ["hvac"],
            "reg": ["bacs"],
        },
        "scope": {
            "hvac_kw_min": 70,
            "building_type": ["bureau", "magasin", "entrepot", "commerce", "hotel", "sante", "enseignement"],
        },
        "logic": {
            "when": {
                "any": [
                    {"all": [{"field": "hvac_kw", "op": ">=", "value": 290}]},
                    {
                        "all": [
                            {"field": "hvac_kw", "op": ">=", "value": 70},
                            {"field": "hvac_kw", "op": "<", "value": 290},
                        ]
                    },
                ]
            },
            "then": {
                "outputs": [
                    {
                        "type": "obligation",
                        "label": "Installation systeme BACS/GTB classe B ou A",
                        "severity": "critical",
                        "deadline": "2025-01-01",
                        "condition": "hvac_kw >= 290",
                    },
                    {
                        "type": "obligation",
                        "label": "Installation systeme BACS/GTB classe B ou A (seuil 70 kW)",
                        "severity": "high",
                        "deadline": "2030-01-01",
                        "condition": "hvac_kw >= 70 et < 290",
                    },
                ]
            },
        },
    },
    {
        "id": "BACS_SEUILS_5",
        "confidence": "high",
        "tags": {"energy": ["elec", "gaz"], "segment": ["tertiaire_multisite"], "asset": ["hvac"], "reg": ["bacs"]},
        "scope": {"hvac_kw_min": 70},
        "logic": {
            "when": {"all": [{"field": "hvac_kw", "op": ">=", "value": 70}]},
            "then": {
                "outputs": [
                    {
                        "type": "knowledge",
                        "label": "Exemption BACS possible si TRI > 10 ans (audit requis, documentation 10 ans)",
                        "severity": "medium",
                    },
                ]
            },
        },
    },
    {
        "id": "BACS_SEUILS_7",
        "confidence": "high",
        "tags": {"energy": ["elec", "gaz"], "segment": ["tertiaire_multisite"], "asset": ["hvac"], "reg": ["bacs"]},
        "scope": {"hvac_kw_min": 70},
        "logic": {
            "when": {"all": [{"field": "hvac_kw", "op": ">=", "value": 70}]},
            "then": {
                "outputs": [
                    {
                        "type": "obligation",
                        "label": "Inspection periodique BACS obligatoire tous les 5 ans (2 ans post-installation)",
                        "severity": "high",
                    },
                ]
            },
        },
    },
    {
        "id": "BACS_COMPLET_6",
        "confidence": "high",
        "tags": {
            "energy": ["elec", "gaz"],
            "segment": ["tertiaire_multisite", "collectivite"],
            "asset": ["hvac"],
            "reg": ["bacs"],
        },
        "scope": {"hvac_kw_min": 70},
    },
    {
        "id": "BACS_COMPLET_9",
        "confidence": "high",
        "tags": {"energy": ["elec", "gaz"], "segment": ["tertiaire_multisite"], "asset": ["hvac"], "reg": ["bacs"]},
        "scope": {"hvac_kw_min": 70},
    },
    {
        "id": "BACS_COMPLET_19",
        "confidence": "high",
        "tags": {"energy": ["elec", "gaz"], "segment": ["tertiaire_multisite"], "asset": ["hvac"], "reg": ["bacs"]},
        "scope": {"hvac_kw_min": 70},
        "logic": {
            "when": {"all": [{"field": "hvac_kw", "op": ">=", "value": 290}]},
            "then": {
                "outputs": [
                    {
                        "type": "obligation",
                        "label": "Risque amende 7 500 EUR par an et par batiment non conforme BACS",
                        "severity": "critical",
                    },
                ]
            },
        },
    },
    {
        "id": "BACS_SEUILS_13",
        "confidence": "high",
        "tags": {"energy": ["elec", "gaz"], "segment": ["tertiaire_multisite"], "asset": ["hvac"], "reg": ["bacs"]},
        "scope": {"hvac_kw_min": 70},
    },
    {
        "id": "BACS_COMPLET_16",
        "confidence": "medium",
        "tags": {"energy": ["elec", "gaz"], "segment": ["tertiaire_multisite"], "asset": ["hvac"], "reg": ["bacs"]},
        "scope": {"hvac_kw_min": 70},
    },
]

# ── Decret Tertiaire items to promote ────────────────────────────────
DT_PROMOTIONS = [
    {
        "id": "DT_OPERAT_2026_1",
        "confidence": "high",
        "tags": {
            "energy": ["elec", "gaz"],
            "segment": ["tertiaire_multisite", "collectivite"],
            "asset": ["multi"],
            "reg": ["decret_tertiaire"],
        },
        "scope": {"surface_m2_min": 1000},
        "logic": {
            "when": {"all": [{"field": "surface_m2", "op": ">=", "value": 1000}]},
            "then": {
                "outputs": [
                    {
                        "type": "obligation",
                        "label": "Declaration consommations sur OPERAT (ADEME) avant 30 sept 2026",
                        "severity": "critical",
                        "deadline": "2026-09-30",
                    },
                    {
                        "type": "obligation",
                        "label": "Objectif reduction -40% a echeance 2030",
                        "severity": "high",
                        "deadline": "2030-12-31",
                    },
                ]
            },
        },
    },
    {
        "id": "DT_OPERAT_2026_2",
        "confidence": "high",
        "tags": {
            "energy": ["elec", "gaz"],
            "segment": ["tertiaire_multisite", "collectivite"],
            "asset": ["multi"],
            "reg": ["decret_tertiaire"],
        },
        "scope": {"surface_m2_min": 1000},
        "logic": {
            "when": {"all": [{"field": "surface_m2", "op": ">=", "value": 1000}]},
            "then": {
                "outputs": [
                    {
                        "type": "obligation",
                        "label": "Site tertiaire >= 1000 m2 : assujetti au Decret Tertiaire",
                        "severity": "high",
                    },
                ]
            },
        },
    },
    {
        "id": "DT_OPERAT_2026_4",
        "confidence": "high",
        "tags": {
            "energy": ["elec", "gaz"],
            "segment": ["tertiaire_multisite"],
            "asset": ["multi"],
            "reg": ["decret_tertiaire"],
        },
        "scope": {"surface_m2_min": 1000},
    },
    {
        "id": "DT_OPERAT_2026_5",
        "confidence": "high",
        "tags": {
            "energy": ["elec", "gaz"],
            "segment": ["tertiaire_multisite"],
            "asset": ["multi"],
            "reg": ["decret_tertiaire"],
        },
        "scope": {"surface_m2_min": 1000},
    },
    {
        "id": "DT_SYNTHESE_0",
        "confidence": "high",
        "tags": {
            "energy": ["elec", "gaz"],
            "segment": ["tertiaire_multisite", "collectivite"],
            "asset": ["multi"],
            "reg": ["decret_tertiaire"],
        },
        "scope": {"surface_m2_min": 1000},
    },
    {
        "id": "DT_SYNTHESE_14",
        "confidence": "high",
        "tags": {
            "energy": ["elec", "gaz"],
            "segment": ["tertiaire_multisite"],
            "asset": ["multi"],
            "reg": ["decret_tertiaire"],
        },
        "scope": {"surface_m2_min": 1000},
        "logic": {
            "when": {"all": [{"field": "surface_m2", "op": ">=", "value": 1000}]},
            "then": {
                "outputs": [
                    {
                        "type": "obligation",
                        "label": "Non-declaration OPERAT : amende 7 500 EUR + mise en demeure",
                        "severity": "critical",
                    },
                    {"type": "obligation", "label": "Non-affichage attestation : amende 1 500 EUR", "severity": "high"},
                ]
            },
        },
    },
    {
        "id": "DT_OPERAT_2026_6",
        "confidence": "high",
        "tags": {
            "energy": ["elec", "gaz"],
            "segment": ["tertiaire_multisite"],
            "asset": ["multi"],
            "reg": ["decret_tertiaire"],
        },
        "scope": {"surface_m2_min": 1000},
    },
    {
        "id": "DT_SYNTHESE_11",
        "confidence": "medium",
        "tags": {
            "energy": ["elec", "gaz"],
            "segment": ["tertiaire_multisite"],
            "asset": ["multi"],
            "reg": ["decret_tertiaire"],
        },
        "scope": {"surface_m2_min": 1000},
    },
]

# ── Loi APER items to promote ───────────────────────────────────────
APER_PROMOTIONS = [
    {
        "id": "LOI_APER_0",
        "confidence": "high",
        "tags": {
            "energy": ["elec"],
            "segment": ["tertiaire_multisite", "collectivite", "industrie"],
            "asset": ["multi"],
            "reg": ["loi_aper"],
        },
        "scope": {},
        "logic": {
            "when": {
                "any": [
                    {"all": [{"field": "parking_area_m2", "op": ">=", "value": 1500}]},
                    {"all": [{"field": "roof_area_m2", "op": ">=", "value": 500}]},
                ]
            },
            "then": {
                "outputs": [
                    {
                        "type": "obligation",
                        "label": "Solarisation parking >10 000 m2 : 50% ombriere PV avant juillet 2026",
                        "severity": "critical",
                        "deadline": "2026-07-01",
                        "condition": "parking_area_m2 >= 10000",
                    },
                    {
                        "type": "obligation",
                        "label": "Solarisation parking >1 500 m2 : 50% ombriere PV avant juillet 2028",
                        "severity": "high",
                        "deadline": "2028-07-01",
                        "condition": "parking_area_m2 >= 1500",
                    },
                    {
                        "type": "obligation",
                        "label": "Solarisation toiture >500 m2 : 30-50% ENR avant janvier 2028",
                        "severity": "high",
                        "deadline": "2028-01-01",
                        "condition": "roof_area_m2 >= 500",
                    },
                ]
            },
        },
    },
    {
        "id": "DT_OPERAT_2026_17",
        "confidence": "high",
        "tags": {
            "energy": ["elec"],
            "segment": ["tertiaire_multisite", "collectivite"],
            "asset": ["multi"],
            "reg": ["loi_aper"],
        },
        "scope": {"parking_area_m2_min": 1500},
        "logic": {
            "when": {"all": [{"field": "parking_area_m2", "op": ">=", "value": 1500}]},
            "then": {
                "outputs": [
                    {
                        "type": "obligation",
                        "label": "Obligation Loi APER : solarisation parking >1 500 m2",
                        "severity": "high",
                        "deadline": "2028-07-01",
                    },
                ]
            },
        },
    },
    {
        "id": "LOI_APER_5",
        "confidence": "high",
        "tags": {
            "energy": ["elec"],
            "segment": ["tertiaire_multisite", "copro"],
            "asset": ["multi"],
            "reg": ["loi_aper", "acc"],
        },
    },
    {
        "id": "LOI_APER_7",
        "confidence": "medium",
        "tags": {
            "energy": ["elec"],
            "segment": ["tertiaire_multisite"],
            "asset": ["multi"],
            "reg": ["loi_aper", "acc"],
        },
    },
]

# ── ACC items to promote ────────────────────────────────────────────
ACC_PROMOTIONS = [
    {
        "id": "ACC_FRANCE_0",
        "confidence": "high",
        "tags": {
            "energy": ["elec"],
            "segment": ["bailleur", "collectivite", "tertiaire_multisite", "copro"],
            "asset": ["multi"],
            "reg": ["acc"],
        },
    },
    {
        "id": "ACC_FRANCE_1",
        "confidence": "high",
        "tags": {
            "energy": ["elec"],
            "segment": ["bailleur", "collectivite", "tertiaire_multisite"],
            "asset": ["multi"],
            "reg": ["acc"],
        },
    },
    {
        "id": "ACC_FRANCE_2",
        "confidence": "high",
        "tags": {
            "energy": ["elec"],
            "segment": ["bailleur", "collectivite", "tertiaire_multisite"],
            "asset": ["multi"],
            "reg": ["acc"],
        },
    },
    {
        "id": "ACC_FRANCE_7",
        "confidence": "high",
        "tags": {
            "energy": ["elec"],
            "segment": ["bailleur", "collectivite", "tertiaire_multisite"],
            "asset": ["multi"],
            "reg": ["acc"],
        },
    },
    {
        "id": "ACC_FRANCE_8",
        "confidence": "high",
        "tags": {
            "energy": ["elec"],
            "segment": ["bailleur", "collectivite", "tertiaire_multisite"],
            "asset": ["multi"],
            "reg": ["acc"],
        },
    },
]

# ── Flex items to promote ───────────────────────────────────────────
FLEX_PROMOTIONS = [
    {
        "id": "FLEX_EFFACEMENT_0",
        "confidence": "high",
        "tags": {
            "energy": ["elec"],
            "segment": ["tertiaire_multisite", "industrie"],
            "asset": ["hvac", "process"],
            "reg": ["multi"],
        },
    },
    {
        "id": "FLEX_EFFACEMENT_34",
        "confidence": "high",
        "tags": {
            "energy": ["elec"],
            "segment": ["tertiaire_multisite", "industrie"],
            "asset": ["hvac", "process"],
            "reg": ["multi"],
        },
    },
    {
        "id": "FLEX_EFFACEMENT_5",
        "confidence": "medium",
        "tags": {
            "energy": ["elec"],
            "segment": ["tertiaire_multisite", "industrie"],
            "asset": ["hvac", "process"],
            "reg": ["multi"],
        },
    },
]

# ── Post-ARENH ──────────────────────────────────────────────────────
ARENH_PROMOTIONS = [
    {
        "id": "POST_ARENH_2026_0",
        "confidence": "high",
        "tags": {
            "energy": ["elec"],
            "segment": ["tertiaire_multisite", "industrie", "collectivite"],
            "asset": ["multi"],
            "reg": ["multi"],
        },
    },
]


ALL_PROMOTIONS = BACS_PROMOTIONS + DT_PROMOTIONS + APER_PROMOTIONS + ACC_PROMOTIONS + FLEX_PROMOTIONS + ARENH_PROMOTIONS


def promote_items():
    """Promote selected draft items to validated with enriched metadata."""
    promoted = 0
    errors = 0

    for promo in ALL_PROMOTIONS:
        item_id = promo["id"]
        item = store.get_item(item_id)
        if not item:
            print(f"  [SKIP] {item_id} not found in DB")
            errors += 1
            continue

        # Update fields
        item["status"] = "validated"
        item["confidence"] = promo.get("confidence", "high")

        if "tags" in promo:
            item["tags"] = promo["tags"]

        if "scope" in promo:
            item["scope"] = promo["scope"]

        if "logic" in promo:
            item["logic"] = promo["logic"]

        item["updated_at"] = "2026-02-11"

        if store.upsert_item(item):
            promoted += 1
            conf = promo.get("confidence", "high")
            has_logic = "logic" in promo
            print(f"  [OK] {item_id:30s} conf={conf:6s} logic={'Y' if has_logic else 'N'}")
        else:
            errors += 1
            print(f"  [ERR] {item_id} upsert failed")

    return promoted, errors


def main():
    print("=" * 60)
    print("KB PROMOTION: Regulatory Drafts -> Validated")
    print("=" * 60)

    promoted, errors = promote_items()

    # Rebuild FTS index
    print("\nRebuilding FTS index...")
    result = indexer.rebuild_index()
    print(f"  Indexed: {result['indexed']}, Errors: {len(result['errors'])}")

    # Stats
    stats = store.get_stats()
    print(f"\nFinal KB Stats:")
    print(f"  Total items:    {stats['total_items']}")
    print(f"  Validated:      {stats['by_status'].get('validated', 0)}")
    print(f"  Drafts:         {stats['by_status'].get('draft', 0)}")
    print(f"  By domain:      {json.dumps(stats['by_domain'])}")
    print(f"\nPromoted: {promoted}, Errors: {errors}")
    print("=" * 60)


if __name__ == "__main__":
    main()
