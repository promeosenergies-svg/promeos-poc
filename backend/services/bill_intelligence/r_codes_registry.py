"""
PROMEOS — Bill Intelligence R-codes registry (Phase L22.2).

Mapping cardinal codes anomaly R19→R31 → titres FR canoniques pour AnomaliesPage UI.

Phase L22.2 audit fix P1 (audit Phase L22 reviewer #2 finding 6 +
audit Phase L20 reviewer #1 finding 5 + Phase L21 reviewer #1 finding 6) :

Avant L22.2 : `_R_CODES_TITLE_FR` 13 entrées HARDCODED dans `routes/billing.py:1518`
→ violation règle d'or "zero business logic in routes/" + maintenance loin du
pipeline `services/bill_intelligence/anomaly_detector.py` qui ajoute les codes.

Après L22.2 : registry colocalisé `services/bill_intelligence/` →
- Au plus près du pipeline `anomaly_detector.py` (cohérence module)
- Backward compat 100% via import alias dans `routes/billing.py`
- Logger warning code R-non-mappé Phase L20.4 préservé

Source des titres FR : docstrings `detect_r2X` cumul Phase H/I/J/L1-L9 + cardinal
métier audit CFO B2B.
"""

from __future__ import annotations


# Phase L22.2 — Mapping cardinal R19→R31 codes → titres FR pour UI AnomaliesPage.
# Synchronisé avec `services/bill_intelligence/anomaly_detector.py` (13 détecteurs).
# Si nouveau code R32+ ajouté au pipeline, ajouter ici aussi (logger warning Phase
# L20.4 + L21.1 alerte fallback générique en runtime).
R_CODES_TITLE_FR: dict[str, str] = {
    "R19": "VNU dormant facturé sans usage",
    "R20": "Variance capacité TURPE > seuil",
    "R21": "CTA divergente vs taux réglementaire",
    "R22": "Accise élec erronée (catégorie T1/T2/HP)",
    "R23": "TURPE facturé en double même période",
    "R24": "TVA appliquée à mauvais taux",
    "R25": "Abonnement divergent vs contrat",
    "R26": "Total facture ≠ Σ lignes (cohérence)",
    "R27": "Conso facturée vs MeterReading divergente",
    "R28": "Prix unitaire énergie divergent contrat",
    "R29": "Chevauchement ou trou période facturation",
    "R30": "Période facturée hors fenêtre contractuelle",
    "R31": "Doublons accise/CSPE/TICFE intra-facture",
}

# Phase L22.2 — Mapping severity bill_anomaly → AnomaliesPage UI (lowercase → UPPERCASE).
# critical/warning/info BillAnomaly Enum → CRITICAL/HIGH/MEDIUM AnomaliesPage SEV_LABEL.
BA_SEVERITY_UI_MAP: dict[str, str] = {
    "critical": "CRITICAL",
    "warning": "HIGH",
    "info": "MEDIUM",
}
