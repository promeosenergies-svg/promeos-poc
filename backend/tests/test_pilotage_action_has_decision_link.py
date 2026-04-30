"""Phase 4bis.3 — Sentinel #30 : drill-down réciproque Décision ↔ Pilotage.

La doctrine §11.3 stipule que l'Energy Manager qui voit une **action
prioritaire** sur Cockpit Pilotage doit pouvoir cliquer pour voir la
**décision exécutive** correspondante (et vice-versa). Sans ce lien
réciproque, le triptyque CFO/EM ne fonctionne pas.

Ce sentinel verrouille les 2 directions :
  1. **Décision → Pilotage** : chaque card de `/api/cockpit/decisions/top3`
     doit exposer un drill-down `/cockpit/jour?focus=action-{id}` (logique
     SoT côté FE `CockpitDecision.jsx:510`)
  2. **Pilotage → Décision** : la page Pilotage doit accepter le param
     `?focus=action-{id}` ET le param `?focus=decision-{rank}` pour
     scroll/highlight (vérification source `CockpitPilotage.jsx`)

Couvre :
  - Présence d'un id stable sur chaque action décision (sinon le link
    ne peut pas matcher)
  - Présence du parsing `?focus=action-` côté FE Pilotage
  - Présence du parsing `?focus=decision-` côté FE Pilotage

Ref : audit Sprint Retro Cockpit Dual Sol2 — sentinel #30 ambigu.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from main import app

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def decisions_payload(client):
    r = client.get("/api/cockpit/decisions/top3?org_id=1")
    assert r.status_code == 200, f"HTTP {r.status_code} sur /api/cockpit/decisions/top3"
    return r.json()


class TestPilotageActionHasDecisionLink:
    # ── Direction 1 : Décision → Pilotage ─────────────────────────────────

    def test_each_decision_has_stable_id(self, decisions_payload):
        """Chaque décision expose un `id` stable pour le drill-down `?focus=action-{id}`."""
        decisions = decisions_payload.get("decisions", [])
        assert decisions, (
            "Sentinel #30 : payload /api/cockpit/decisions/top3 doit retourner ≥ 1 décision pour valider le drill-down"
        )
        for d in decisions:
            assert "id" in d and d["id"] is not None, (
                f"Sentinel #30 : chaque décision doit avoir un `id` stable, trouvé : {d}"
            )
            assert isinstance(d["id"], (int, str)), (
                f"Sentinel #30 : `id` doit être int ou str, trouvé {type(d['id'])} = {d['id']}"
            )

    def test_decision_card_renders_focus_action_link_in_fe(self):
        """`CockpitDecision.jsx` génère bien `/cockpit/jour?focus=action-{id}`."""
        fe_file = REPO_ROOT / "frontend" / "src" / "pages" / "CockpitDecision.jsx"
        src = fe_file.read_text(encoding="utf-8")
        assert "/cockpit/jour?focus=action-${" in src, (
            "Sentinel #30 direction Décision→Pilotage : "
            "`CockpitDecision.jsx` doit générer un Link "
            "`/cockpit/jour?focus=action-${decision.id}` (cf doctrine §11.3 "
            "drill-down réciproque)"
        )

    # ── Direction 2 : Pilotage → Décision ─────────────────────────────────

    def test_pilotage_handles_focus_action_param(self):
        """`CockpitPilotage.jsx` parse bien le param `?focus=action-{id}`."""
        fe_file = REPO_ROOT / "frontend" / "src" / "pages" / "CockpitPilotage.jsx"
        src = fe_file.read_text(encoding="utf-8")
        # Pattern : usage de URLSearchParams ou useSearchParams + 'focus'
        # ET référence "action-" pour matcher le slug
        assert "focus" in src and "action-" in src, (
            "Sentinel #30 direction Pilotage→Décision : "
            "`CockpitPilotage.jsx` doit parser le param `?focus=action-{id}` "
            "pour scroll/highlight l'action correspondante"
        )

    def test_pilotage_handles_focus_decision_param(self):
        """`CockpitPilotage.jsx` parse aussi `?focus=decision-{rank}` (alias)."""
        fe_file = REPO_ROOT / "frontend" / "src" / "pages" / "CockpitPilotage.jsx"
        src = fe_file.read_text(encoding="utf-8")
        assert "decision-" in src, (
            "Sentinel #30 : `CockpitPilotage.jsx` doit aussi accepter "
            "`?focus=decision-{rank}` (alias pour drill-down depuis Vue "
            "exécutive avec rank 1-3 au lieu d'id action)"
        )

    # ── Cohérence : pas de drift naming entre les 2 directions ────────────

    def test_no_legacy_anchor_pattern(self):
        """Pas d'ancre legacy `#decision-{rank}` non gérée par React Router."""
        # Phase 17.bis.D avait migré de `#decision-X` vers `?focus=...`
        # parce que les ancres ne survivaient pas au PageSuspense lazy.
        # Si un futur PR réintroduit le pattern `#decision-`, on alerte.
        fe_file = REPO_ROOT / "frontend" / "src" / "pages" / "CockpitDecision.jsx"
        src = fe_file.read_text(encoding="utf-8")
        # On autorise `decision-` dans les commentaires d'historique mais pas
        # dans un `to=` ou `href=` actif.
        bad_patterns = ["to=`/cockpit/jour#decision-", 'href="/cockpit/jour#decision-']
        for pat in bad_patterns:
            assert pat not in src, (
                f"Sentinel #30 régression : `CockpitDecision.jsx` ne doit pas "
                f"utiliser le pattern legacy `{pat}` (ancres cassées par "
                f"PageSuspense lazy, cf Phase 17.bis.D)"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
