"""
PROMEOS — References legales par rule_id.

Source de verite backend pour les references legales associees a chaque finding.
Synchronise avec frontend/src/domain/compliance/complianceLabels.fr.js (RULE_LEGAL_REFS).
"""

LEGAL_REFS = {
    # Decret Tertiaire
    "SCOPE_UNKNOWN": {
        "ref": "Decret n2019-771 du 23/07/2019, Art. R174-22 CCH",
        "label": "Decret Tertiaire — Champ d'application",
        "url": "https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000038812251",
        "kb_item_id": "rule-decret-tertiaire",
    },
    "OUT_OF_SCOPE": {
        "ref": "Decret n2019-771, Art. R174-22 — seuil 1000 m2",
        "label": "Decret Tertiaire — Hors perimetre",
        "url": "https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000038812251",
        "kb_item_id": "rule-decret-tertiaire",
    },
    "OPERAT_NOT_STARTED": {
        "ref": "Arrete du 10 avril 2020, Art. 3",
        "label": "Plateforme OPERAT — Declaration annuelle",
        "url": "https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000041842389",
        "kb_item_id": "reg-arrete-2020-04-10",
    },
    "ENERGY_DATA_MISSING": {
        "ref": "Decret n2019-771, Art. R174-23",
        "label": "Obligation de suivi des consommations",
        "url": "https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000038812251",
    },
    "MULTI_OCCUPIED_GOVERNANCE": {
        "ref": "Decret n2019-771, Art. R174-24",
        "label": "Repartition obligations proprietaire/locataire",
        "url": "https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000038812251",
    },
    # BACS
    "BACS_ABOVE_290KW": {
        "ref": "Decret n2020-887 du 20/07/2020, Art. R175-2",
        "label": "GTB/GTC — CVC > 290 kW (echeance 2025)",
        "url": "https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000042121844",
    },
    "BACS_70_TO_290KW": {
        "ref": "Decret n2020-887 modifie, Art. R175-2",
        "label": "GTB/GTC — CVC 70-290 kW (echeance 2030)",
        "url": "https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000042121844",
    },
    "BACS_MISSING_CVC_POWER": {
        "ref": "Decret n2020-887, Art. R175-2",
        "label": "Puissance CVC non renseignee",
        "url": "https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000042121844",
    },
    # APER
    "PARKING_LARGE_APER": {
        "ref": "Loi n2023-175 (APER) du 10/03/2023, Art. 40",
        "label": "Ombrieres photovoltaiques — Parking >= 10 000 m2",
        "url": "https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000047294244",
    },
    "PARKING_MEDIUM_APER": {
        "ref": "Loi APER, Art. 40",
        "label": "Ombrieres photovoltaiques — Parking >= 1 500 m2",
        "url": "https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000047294244",
    },
    "ROOF_ABOVE_THRESHOLD": {
        "ref": "Loi APER, Art. 41",
        "label": "ENR en toiture — Surface >= 500 m2",
        "url": "https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000047294244",
    },
    # CEE
    "CEE_OPPORTUNITY_GTB": {
        "ref": "Dispositif CEE (periode P6)",
        "label": "Certificat d'economies d'energie — opportunite GTB",
    },
}


def get_legal_ref(rule_id: str) -> dict | None:
    """Retourne la reference legale pour un rule_id donne."""
    return LEGAL_REFS.get(rule_id)
