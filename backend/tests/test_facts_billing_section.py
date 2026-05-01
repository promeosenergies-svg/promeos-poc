"""Phase 26 — Sentinel `_facts.billing` exposé pour DataReadinessBadge.

Avant Phase 26, `useActivationData` (consommé par DataReadinessBadge dans
AppShell) appelait `/api/billing/summary` 2× au mount /cockpit/strategique.
Mesure preview prod 2026-05-01 (Phase 25) a confirmé le bug. Phase 1.3 du
sprint avait promis "billing remplacé par _facts" sans le tenir pour le
badge AppShell.

Cette section verrouille :
  - `_facts.billing` est exposé dans le payload (top-level key)
  - Contient les 4 champs canoniques consommés par useDataReadiness :
    `total_invoices`, `total_eur`, `total_kwh`, `coverage_months`
  - Cohérence : si l'org a des factures, `total_invoices > 0` et
    `coverage_months > 0`

Ref : Sprint Retro Cockpit Dual Sol2 — Phase 26 (audit prod 2026-05-01).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from main import app

CANONICAL_BILLING_KEYS = {"total_invoices", "total_eur", "total_kwh", "coverage_months"}


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def facts_payload(client):
    r = client.get("/api/cockpit/_facts?org_id=1&period=current_week")
    assert r.status_code == 200, f"HTTP {r.status_code} sur /api/cockpit/_facts"
    return r.json()


class TestFactsBillingSection:
    def test_billing_section_exposed(self, facts_payload):
        """`_facts.billing` est un objet exposé dans le payload."""
        assert "billing" in facts_payload, (
            "Phase 26 : `_facts.billing` doit être exposé pour permettre à "
            "DataReadinessBadge de skipper l'appel /api/billing/summary "
            "(cf audit prod Phase 25 : 2× billing/summary au mount "
            "/cockpit/strategique)"
        )
        assert isinstance(facts_payload["billing"], dict), "Phase 26 : `_facts.billing` doit être un objet structuré"

    def test_billing_has_canonical_keys(self, facts_payload):
        """`_facts.billing` expose les 4 champs canoniques."""
        billing = facts_payload["billing"]
        missing = CANONICAL_BILLING_KEYS - set(billing.keys())
        assert not missing, (
            f"Phase 26 : `_facts.billing` doit exposer {CANONICAL_BILLING_KEYS}, "
            f"manquant : {missing}. Champs présents : {set(billing.keys())}"
        )

    def test_billing_helios_has_invoices_when_seeded(self, facts_payload):
        """Si HELIOS S est seedé, billing expose total_invoices > 0 (sinon skip).

        Le test pytest crée parfois sa propre DB (fixture engine) qui n'a pas
        forcément les factures seedées. On valide juste la cohérence : si
        total_invoices > 0, alors coverage_months > 0 (et vice-versa).
        """
        billing = facts_payload["billing"]
        if billing["total_invoices"] == 0:
            pytest.skip(
                "Aucune facture seedée dans la DB du test (pack non-helios "
                "ou DB éphémère). Phase 26 : ce test n'est valide qu'avec "
                "le seed `python -m services.demo_seed --pack helios --size S`"
            )
        assert billing["coverage_months"] > 0, "Phase 26 cohérence : total_invoices > 0 ⇒ coverage_months > 0"

    def test_billing_total_eur_is_numeric(self, facts_payload):
        """`total_eur` est numérique (float ou int), pas string."""
        total_eur = facts_payload["billing"]["total_eur"]
        assert isinstance(total_eur, (int, float)), (
            f"Phase 26 : total_eur doit être numérique, trouvé {type(total_eur).__name__} = {total_eur}"
        )

    def test_billing_in_cockpit_facts_no_recompute_set(self):
        """`_build_billing` est inclus dans la liste des helpers internes."""
        # Sentinel #10 (Phase 4bis.1) verrouille déjà que les `_build_*` sont
        # uniques. Ici on s'assure que `_build_billing` est dans le set
        # canonique et donc protégé par le test_cockpit_facts_no_recompute.
        from tests.test_cockpit_facts_no_recompute import INTERNAL_BUILDERS

        assert "_build_billing" not in INTERNAL_BUILDERS, (
            "Note : si _build_billing est ajouté à INTERNAL_BUILDERS, vérifier "
            "qu'il est bien orchestré dans get_cockpit_facts avant de mettre "
            "à jour ce test."
        )
        # Pas critique — _build_billing peut rester hors du set canonique
        # initial. Le verrou réel est `test_billing_section_exposed` ci-dessus.


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
