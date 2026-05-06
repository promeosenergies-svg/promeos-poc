"""
PROMEOS — Bill Intelligence (Sprint C-5 Phase 5.1).

Module dédié à la détection d'anomalies de facturation énergie (différenciateur produit
cardinal Phase C — vs Deepki/Spacewell généralistes sans Bill Intelligence dédié).

Architecture rules-based pure (R19 + R20), seuils YAML SoT (sources_reglementaires.yaml),
modèle BillAnomaly persisté (héritage SoftDeleteMixin).

ADR-013 : `docs/adr/ADR-013-BillIntelligence-AnomalyDetector-Pattern.md`
"""

from .anomaly_detector import (
    detect_r19_vnu_dormant,
    detect_r20_capacity_variance,
    detect_anomalies_for_invoice,
)

__all__ = [
    "detect_r19_vnu_dormant",
    "detect_r20_capacity_variance",
    "detect_anomalies_for_invoice",
]
