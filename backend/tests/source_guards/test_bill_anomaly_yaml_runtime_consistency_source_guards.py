"""
PROMEOS — Source guards Bill Intelligence YAML ↔ runtime cohérence (Sprint C-5 Phase 5.1, ADR-013).

Anti-régression cardinal post-création module bill_intelligence (différenciateur produit
Phase C). Garantit :

- SG_BILL_ANOMALY_01 : 2 termes YAML BILL_ANOMALY_* présents dans
  `config/sources_reglementaires.yaml` (domain `bill_intelligence`)
- SG_BILL_ANOMALY_02 : runtime `services/bill_intelligence/anomaly_detector.py` ne
  hard-code AUCUNE valeur 0.01 EUR ou 5.0 % en dur (allowlist commentaires uniquement)
- SG_BILL_ANOMALY_03 : helper `_resolve_period_code` signature stable (3 priorités préservées)

Si quelqu'un duplique un seuil hard-codé ou retire un terme YAML sans coordonner les
callsites, ces SG flaggent à la collection pytest.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_YAML_PATH = _BACKEND_ROOT / "config" / "sources_reglementaires.yaml"
_DETECTOR_PATH = _BACKEND_ROOT / "services" / "bill_intelligence" / "anomaly_detector.py"


def test_sg_bill_anomaly_01_yaml_terms_present():
    """SG_BILL_ANOMALY_01 : 2 termes BILL_ANOMALY_* présents YAML domain bill_intelligence."""
    content = _YAML_PATH.read_text(encoding="utf-8")

    cardinal_terms = [
        "BILL_ANOMALY_VNU_DORMANT_THRESHOLD_EUR",
        "BILL_ANOMALY_CAPACITY_VARIANCE_THRESHOLD_PCT",
    ]

    missing = [t for t in cardinal_terms if t not in content]
    assert not missing, (
        f"Termes YAML manquants dans sources_reglementaires.yaml : {missing}.\n"
        "Sprint C-5 Phase 5.1 (ADR-013) requiert ces 2 termes pour seuils anomaly_detector. "
        "Si suppression intentionnelle, coordonner avec services/bill_intelligence/anomaly_detector.py."
    )

    # Vérifier domain bill_intelligence
    assert 'domain: "bill_intelligence"' in content, (
        "Domain 'bill_intelligence' absent de sources_reglementaires.yaml. "
        "Les 2 termes BILL_ANOMALY_* doivent être dans ce domain."
    )


def test_sg_bill_anomaly_02_no_hardcoded_threshold():
    """SG_BILL_ANOMALY_02 : detector n'hard-code pas les seuils (chargement YAML obligatoire)."""
    content = _DETECTOR_PATH.read_text(encoding="utf-8")

    # Le module doit charger les seuils via get_term_value
    assert 'get_term_value("BILL_ANOMALY_VNU_DORMANT_THRESHOLD_EUR")' in content, (
        "anomaly_detector.py doit charger BILL_ANOMALY_VNU_DORMANT_THRESHOLD_EUR via get_term_value. "
        "Hard-code = drift YAML ↔ runtime garanti."
    )
    assert 'get_term_value("BILL_ANOMALY_CAPACITY_VARIANCE_THRESHOLD_PCT")' in content, (
        "anomaly_detector.py doit charger BILL_ANOMALY_CAPACITY_VARIANCE_THRESHOLD_PCT via get_term_value."
    )

    # Allowlist : pas de valeur magique 0.01 ou 5.0 hors commentaires/docstrings
    code_lines = []
    in_docstring = False
    for raw_line in content.splitlines():
        stripped = raw_line.strip()
        # Skip docstring blocks (triple-quoted)
        if stripped.startswith('"""') or stripped.startswith("'''"):
            in_docstring = not in_docstring or (stripped.count('"""') == 2 or stripped.count("'''") == 2)
            continue
        if in_docstring:
            continue
        # Skip comments
        if stripped.startswith("#"):
            continue
        code_lines.append(raw_line)

    code_only = "\n".join(code_lines)

    # Pattern : assignement ou comparaison numérique avec 0.01 ou 5.0 isolés
    forbidden_patterns = [
        r"=\s*0\.01\b",  # threshold = 0.01
        r"=\s*5\.0\b",  # threshold_pct = 5.0
    ]
    for pattern in forbidden_patterns:
        match = re.search(pattern, code_only)
        assert not match, (
            f"Hard-code interdit détecté dans anomaly_detector.py (pattern '{pattern}').\n"
            f"Ligne suspecte : {match.group(0) if match else '?'}\n"
            "Charger via get_term_value depuis sources_reglementaires.yaml."
        )


def test_sg_bill_anomaly_03_resolve_period_code_signature_stable():
    """SG_BILL_ANOMALY_03 : helper _resolve_period_code signature préservée."""
    content = _DETECTOR_PATH.read_text(encoding="utf-8")

    assert "def _resolve_period_code(line: EnergyInvoiceLine) -> Optional[str]:" in content, (
        "Signature _resolve_period_code(line: EnergyInvoiceLine) -> Optional[str] modifiée.\n"
        "3 priorités cardinales (champ direct / meta_json / label) doivent être préservées.\n"
        "Adaptation Phase 5.1.0 — matching ps_par_poste_kva[period_code] dépend de cette extraction."
    )

    # Vérifier les 3 priorités (commentaires explicites)
    cardinal_markers = [
        "Priorité 1",
        "Priorité 2",
        "Priorité 3",
    ]
    missing_markers = [m for m in cardinal_markers if m not in content]
    assert not missing_markers, (
        f"Marqueurs Priorité absents : {missing_markers}.\n"
        "Documentation cardinal sur la stratégie de matching period_code requise."
    )
