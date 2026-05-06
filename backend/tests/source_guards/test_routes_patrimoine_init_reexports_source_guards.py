"""
PROMEOS — Source guard ré-exports `routes/patrimoine/__init__.py` (Sprint C-4 Phase 4.7).

Anti-régression cardinal post-V92 split (Sprint C-2) : les tests + services importent
massivement `from routes.patrimoine import X` (~17 callsites) alors que le code
métier a été éclaté dans `staging.py / sites.py / compteurs.py / contracts.py /
billing.py / _helpers.py`. La cohabitation est assurée par les ré-exports dans
`__init__.py` (`# Backward-compatible re-exports`).

Si quelqu'un retire un ré-export sans coordonner les callsites, les imports
deviennent stale silencieusement et les tests cassent à la collection (ImportError).

Ce SG vérifie que le pattern de ré-exports cardinal reste présent (ne valide pas
chaque symbole — la vérification effective se fait à la collection pytest).

Clôture dette `D-V92-Split-Stale-Imports-Audit-001` P2 (audit Phase 4.7.1 :
137 tests collectés sans erreur sur les fichiers post-V92 split).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_PATRIMOINE_INIT = _BACKEND_ROOT / "routes" / "patrimoine" / "__init__.py"


def test_sg_v92_patrimoine_init_has_backward_compat_reexports():
    """SG_V92_01 : `routes/patrimoine/__init__.py` contient le bloc de ré-exports
    backward-compat (cardinal pour `from routes.patrimoine import X` legacy).
    """
    content = _PATRIMOINE_INIT.read_text(encoding="utf-8")

    # Marqueur cardinal du bloc de ré-exports
    assert "Backward-compatible re-exports" in content, (
        "Bloc 'Backward-compatible re-exports' absent de routes/patrimoine/__init__.py.\n"
        "Risque : ~17 tests `from routes.patrimoine import X` cassent à la collection.\n"
        "Restaurer le bloc ou coordonner les callsites consumers."
    )


def test_sg_v92_patrimoine_init_reexports_cardinal_helpers():
    """SG_V92_02 : ré-exports cardinaux présents (`_get_org_id` + `_serialize_*` +
    `_check_*_belongs_to_org` + `_load_*_with_org_check`). Liste minimale anti-régression.
    """
    content = _PATRIMOINE_INIT.read_text(encoding="utf-8")

    cardinal_reexports = [
        "_get_org_id",
        "_check_site_belongs_to_org",
        "_check_portfolio_belongs_to_org",
        "_load_site_with_org_check",
        "_load_compteur_with_org_check",
        "_load_contract_with_org_check",
        "_serialize_site",
        "_serialize_contract",
        "_compute_site_completeness",
        "_worst_compliance_status",
    ]

    missing = [name for name in cardinal_reexports if name not in content]
    assert not missing, (
        f"Ré-exports cardinaux manquants dans routes/patrimoine/__init__.py : {missing}.\n"
        "Ces helpers sont consommés par ~17 callsites (tests + services). "
        "Coordonner avant suppression."
    )
