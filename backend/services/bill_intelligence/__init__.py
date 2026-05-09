"""
PROMEOS — Bill Intelligence (Sprint C-5 Phase 5.1).

Module dédié à la détection d'anomalies de facturation énergie (différenciateur produit
cardinal Phase C — vs Deepki/Spacewell généralistes sans Bill Intelligence dédié).

Architecture rules-based pure (R19 + R20), seuils YAML SoT (sources_reglementaires.yaml),
modèle BillAnomaly persisté (héritage SoftDeleteMixin).

ADR-013 : `docs/adr/ADR-013-BillIntelligence-AnomalyDetector-Pattern.md`
"""

from .anomaly_detector import (
    build_contract_cache,
    build_dp_category_cache,
    build_prev_invoice_cache,
    detect_anomalies_for_invoice,
    detect_r19_vnu_dormant,
    detect_r20_capacity_variance,
)
from .priority import severity_to_priority_score
from .r_codes_registry import BA_SEVERITY_UI_MAP, R_CODES_TITLE_FR

__all__ = [
    # Détecteurs cardinaux
    "detect_r19_vnu_dormant",
    "detect_r20_capacity_variance",
    "detect_anomalies_for_invoice",
    # Phase L7.3 + L12 + L23.1 — caches batch pré-construits
    "build_prev_invoice_cache",
    "build_contract_cache",
    "build_dp_category_cache",
    # Phase L22.1 + L22.2 — helpers UI cardinal cross-callsites
    "severity_to_priority_score",
    "R_CODES_TITLE_FR",
    "BA_SEVERITY_UI_MAP",
]
