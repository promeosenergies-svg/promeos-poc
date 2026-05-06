"""
PROMEOS — Tests cardinaux Phase 7.7 Sprint C-7 Lot A — Bill Anomaly enrichissements.

Couvre 4 P1 + 3 P2 dettes Sprint C-7 :
- D-Sprint-C7-BillAnomaly-Multi-Postes-HTA-001 P1 (HPE/HCE/PM dans _PERIOD_CODES_KNOWN)
- D-Sprint-C7-BillAnomaly-PII-Vnu-Labels-Sanitization-001 P1 (sanitizer SIREN/PRM)
- D-Sprint-C7-BillAnomaly-Thresholds-Source-001 P1 (YAML legal_reference enrichi)
- D-Sprint-C7-BillAnomaly-Unique-Constraint-001 P1 (déjà fait Phase 5.8 G3, marqué CLÔTURÉE)
- D-Sprint-C7-BillAnomaly-Decoupling-Commit-001 P2 (db.commit() retiré)
- D-Sprint-C7-BillAnomaly-Word-Boundary-Regex-001 P2 (regex \\b<code>\\b)
"""

from __future__ import annotations


def test_phase77_lot_a_period_codes_includes_hta_codes():
    """Phase 7.7 Lot A : _PERIOD_CODES_KNOWN inclut HPE/HCE/PM (TURPE 7 HTA)."""
    from services.bill_intelligence.anomaly_detector import _PERIOD_CODES_KNOWN

    cardinal_hta = ["HPE", "HCE", "PM"]
    missing = [c for c in cardinal_hta if c not in _PERIOD_CODES_KNOWN]
    assert not missing, (
        f"Phase 7.7 Lot A BLOQUANT : codes HTA manquants : {missing}.\n"
        "TURPE 7 HTA exige HPE (Heures de Pointe d'Été), HCE (Heures Creuses d'Été), "
        "PM (Pointe Mobile). Sans ces codes, R20 silencieusement aveugle sur sites HTA."
    )


def test_phase77_lot_a_resolve_period_code_word_boundary_anti_false_positive():
    """Phase 7.7 Lot A : `_resolve_period_code` regex \\b<code>\\b évite faux-positifs.

    Avant fix : "CHC" matchait "HC" via substring → false positive.
    Après fix : word-boundary requiert séparateurs autour du code.
    """
    from services.bill_intelligence.anomaly_detector import _resolve_period_code

    class _FakeLine:
        def __init__(self, label):
            self.label = label
            self.period_code = None
            self.meta_json = None

    # CHC ne doit PAS matcher HC (anti-régression word-boundary)
    line_chc = _FakeLine("CHARGE CHC FACTURATION")
    assert _resolve_period_code(line_chc) is None or _resolve_period_code(line_chc) != "HC"

    # "HC SOIRE" doit matcher HC (word-boundary OK)
    line_hc = _FakeLine("CONSO HC SOIRE")
    assert _resolve_period_code(line_hc) == "HC"


def test_phase77_lot_a_pii_sanitization_redacts_siren_in_vnu_labels():
    """Phase 7.7 Lot A cardinal : labels VNU avec SIREN/PRM masqués `<PII_REDACTED>`."""
    from services.bill_intelligence.anomaly_detector import _sanitize_pii_label

    # SIREN (9 chiffres)
    label_siren = "VNU TotalEnergies 552032534 facture 2026-03"
    sanitized = _sanitize_pii_label(label_siren)
    assert "552032534" not in sanitized
    assert "<PII_REDACTED>" in sanitized

    # PRM/SIRET (14 chiffres)
    label_prm = "VNU PRM 12345678901234 dormant"
    sanitized2 = _sanitize_pii_label(label_prm)
    assert "12345678901234" not in sanitized2
    assert "<PII_REDACTED>" in sanitized2

    # Label sans PII inchangé
    label_clean = "VNU dormant compteur principal"
    assert _sanitize_pii_label(label_clean) == label_clean


def test_phase77_lot_a_pii_sanitization_handles_none_and_empty():
    """Phase 7.7 Lot A : sanitizer gracieux sur label vide/None."""
    from services.bill_intelligence.anomaly_detector import _sanitize_pii_label

    assert _sanitize_pii_label("") == ""
    assert _sanitize_pii_label(None) is None  # type: ignore — defensive


def test_phase77_lot_a_yaml_legal_reference_enriched():
    """Phase 7.7 Lot A : YAML BILL_ANOMALY_VNU_DORMANT + CAPACITY_VARIANCE legal_reference."""
    from config.regulatory_sources_loader import get_term

    vnu_term = get_term("BILL_ANOMALY_VNU_DORMANT_THRESHOLD_EUR")
    cap_term = get_term("BILL_ANOMALY_CAPACITY_VARIANCE_THRESHOLD_PCT")

    # Cardinal : URL + legal_reference enrichis (vs null avant Phase 7.7)
    assert vnu_term["source"]["url"] is not None
    assert "legifrance" in vnu_term["source"]["url"].lower()
    assert "L.336-2" in vnu_term["source"]["legal_reference"]

    assert cap_term["source"]["url"] is not None
    assert "cre.fr" in cap_term["source"]["url"].lower()
    assert "TURPE 7" in cap_term["source"]["legal_reference"]


def test_phase77_lot_a_pipeline_caller_responsable_commit():
    """Phase 7.7 Lot A : `detect_anomalies_for_invoice` ne commit plus (caller responsable)."""
    import inspect

    from services.bill_intelligence.anomaly_detector import detect_anomalies_for_invoice

    src = inspect.getsource(detect_anomalies_for_invoice)
    # Filtrer commentaires/docstring — vérifier appel runtime uniquement
    runtime_lines = [
        line for line in src.split("\n") if "db.commit()" in line and not line.strip().startswith(("#", '"', "'"))
    ]
    # Tolérance docstring (ligne dans """ block) — tout sauf appel direct
    runtime_calls = [
        line for line in runtime_lines if "db.commit()" in line and "retiré" not in line and "retire" not in line
    ]
    assert not any(line.strip() == "db.commit()" for line in runtime_calls), (
        "Phase 7.7 Lot A BLOQUANT : `detect_anomalies_for_invoice` contient encore db.commit() runtime.\n"
        "Decoupling pattern : caller décide quand commit (transactional batch / unit-of-work)."
    )
    # Mention Phase 7.7 Lot A dans docstring
    assert "Phase 7.7 Lot A" in src or "Decoupling" in src


def test_phase77_lot_a_billanomaly_unique_constraint_present():
    """Phase 7.7 Lot A : UNIQUE(invoice_id, code) déjà livré Phase 5.8 G3 — verif anti-régression."""
    from models.bill_anomaly import BillAnomaly

    constraints = [c for c in BillAnomaly.__table_args__ if hasattr(c, "name")]
    unique_names = [c.name for c in constraints if "uq_bill_anomaly" in (c.name or "")]
    assert "uq_bill_anomaly_invoice_code" in unique_names, (
        "Phase 7.7 Lot A : UNIQUE constraint perdue (régression Phase 5.8 G3).\n"
        "Anti-doublons concurrents R19/R20 critique."
    )
