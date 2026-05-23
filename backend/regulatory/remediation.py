"""PROMEOS — Mapping canonique `reason_code` DATA_MISSING → instructions de remédiation FR.

P0-B 2026-05-23 — rend les `DATA_MISSING` actionnables côté frontend :
chaque code expose le champ patrimoine à corriger (`remediation_field`), son
niveau (`site` / `batiment` / `organisation` / `entite_juridique`), un libellé
FR utilisateur, une explication courte FR et un CTA prêt à afficher.

SoT unique consommée par `RuleApplicability.to_dict()` (auto-enrichissement
côté API). Verrouillée par `tests/source_guards/test_data_missing_remediation_source_guards.py`
qui exige une entrée pour chaque code DATA_MISSING listé dans `reason_codes.py`.

Source juridique des libellés : matrice v1 §4.4 / §4.5 + audit
`docs/audits/audit_brique_patrimoine_deep_readonly_2026_05_23.md` §6.
"""

from __future__ import annotations

from typing import Final, TypedDict


class Remediation(TypedDict):
    """Instructions de remédiation pour un `reason_code` DATA_MISSING."""

    remediation_field: str  # ex "site.tertiaire_area_m2"
    remediation_level: str  # "site" | "batiment" | "organisation" | "entite_juridique"
    remediation_label_fr: str  # libellé du champ pour l'utilisateur
    remediation_hint_fr: str  # explication courte FR (pourquoi ce champ)
    cta_label_fr: str  # texte du bouton d'action


# Mapping cardinal : chaque code DATA_MISSING listé dans `reason_codes.py`
# doit avoir une entrée ici (verrou source-guard).
REASON_CODE_TO_REMEDIATION: Final[dict[str, Remediation]] = {
    # ── Décret Tertiaire ─────────────────────────────────────────────────────
    "DT.DATA_MISSING.SURFACE": {
        "remediation_field": "site.tertiaire_area_m2",
        "remediation_level": "site",
        "remediation_label_fr": "Surface tertiaire",
        "remediation_hint_fr": (
            "Renseignez la surface tertiaire pour confirmer si le site est "
            "soumis au Décret Tertiaire."
        ),
        "cta_label_fr": "Compléter la surface",
    },
    "DT.DATA_MISSING.USAGE": {
        "remediation_field": "site.usage_principal",
        "remediation_level": "site",
        "remediation_label_fr": "Usage principal du site",
        "remediation_hint_fr": (
            "Précisez l'usage principal du site (bureaux, commerce, santé, etc.) "
            "pour déterminer l'assujettissement au Décret Tertiaire."
        ),
        "cta_label_fr": "Préciser l'usage",
    },
    # ── BACS (Décret 2020-887) ──────────────────────────────────────────────
    "BACS.DATA_MISSING.CVC_POWER": {
        "remediation_field": "batiment.cvc_power_kw",
        "remediation_level": "batiment",
        "remediation_label_fr": "Puissance CVC",
        "remediation_hint_fr": (
            "Renseignez la puissance chauffage/climatisation (en kW) pour "
            "vérifier l'obligation BACS du bâtiment."
        ),
        "cta_label_fr": "Compléter la puissance CVC",
    },
    # ── APER (Loi 2023-175 art. 40) ─────────────────────────────────────────
    "APER.DATA_MISSING.PARKING_AREA": {
        "remediation_field": "site.parking_area_m2",
        "remediation_level": "site",
        "remediation_label_fr": "Surface de parking",
        "remediation_hint_fr": (
            "Renseignez la surface de parking extérieur (en m²) pour vérifier "
            "l'obligation de solarisation APER."
        ),
        "cta_label_fr": "Compléter le parking",
    },
    "APER.DATA_MISSING.ROOF_AREA": {
        "remediation_field": "site.roof_area_m2",
        "remediation_level": "site",
        "remediation_label_fr": "Surface de toiture",
        "remediation_hint_fr": (
            "Renseignez la surface de toiture (en m²) pour évaluer le potentiel "
            "solaire et l'obligation APER."
        ),
        "cta_label_fr": "Compléter la toiture",
    },
    # ── Audit Énergétique / SMÉ ─────────────────────────────────────────────
    "SME.DATA_MISSING.EFFECTIF": {
        "remediation_field": "organisation.effectif_total",
        "remediation_level": "organisation",
        "remediation_label_fr": "Effectif de l'organisation",
        "remediation_hint_fr": (
            "Renseignez l'effectif total pour déterminer si l'organisation est "
            "assujettie à l'audit énergétique réglementaire."
        ),
        "cta_label_fr": "Compléter l'effectif",
    },
    "SME.DATA_MISSING.CA": {
        "remediation_field": "organisation.chiffre_affaires_eur",
        "remediation_level": "organisation",
        "remediation_label_fr": "Chiffre d'affaires",
        "remediation_hint_fr": (
            "Renseignez le chiffre d'affaires annuel et le bilan pour appliquer "
            "les seuils SMÉ (Code énergie L233-1)."
        ),
        "cta_label_fr": "Compléter le CA",
    },
    "SME.DATA_MISSING.CONSO": {
        "remediation_field": "entite_juridique.consommation_annuelle_moyenne_3y_gwh",
        "remediation_level": "entite_juridique",
        "remediation_label_fr": "Consommation moyenne 3 ans",
        "remediation_hint_fr": (
            "Renseignez la consommation moyenne 3 ans (GWh) pour appliquer le "
            "seuil Audit SMÉ DDADUE 2025-391."
        ),
        "cta_label_fr": "Compléter la consommation",
    },
    # ── BEGES (Grenelle 2 art. 75) ──────────────────────────────────────────
    "BEGES.DATA_MISSING.EFFECTIF": {
        "remediation_field": "organisation.effectif_total",
        "remediation_level": "organisation",
        "remediation_label_fr": "Effectif de l'organisation",
        "remediation_hint_fr": (
            "Renseignez l'effectif pour évaluer l'obligation BEGES "
            "(seuil 500 métropole / 250 DOM)."
        ),
        "cta_label_fr": "Compléter l'effectif",
    },
}


def get_remediation(reason_code: str) -> Remediation | None:
    """Retourne les instructions de remédiation pour un `reason_code` DATA_MISSING.

    Retourne `None` pour les codes hors mapping (APPLICABLE, NOT_APPLICABLE,
    UNKNOWN, …) — ils n'ont pas vocation à être actionnables.
    """
    return REASON_CODE_TO_REMEDIATION.get(reason_code)
