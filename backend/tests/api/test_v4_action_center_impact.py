"""M2-5.10.C — Tests de GET /api/v4/action-center/items/{id}/impact.

Couverture :
- Auth : 401 sans token, 200 VIEWER/USER/ADMIN
- IDOR cardinal : item inexistant → 404, item cross-org → 404 (anti-leak)
- Réponse structurée : 4 quadrants présents, has_data dérivé
- Cas vide : impact_payload null → tous les value_eur=null + has_data=False
- Cas peuplé : impact_payload structuré → quadrants lus, has_data=True
- Cas partiel : 1 seule dimension peuplée → has_data=True, autres null
- Cardinaux service : pas de calcul dérivé (impact_payload manquant → null,
  jamais d'invention d'une valeur depuis priority_bracket)

Fixtures : `client`, `viewer_token`, `user_token`, `seeded_item`
(conftest api). DB in-memory SQLite isolée (`app_client`).
"""

import uuid

from models.v4.action_center_items import ActionCenterItem

ITEMS = "/api/v4/action-center/items"


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ════════════════════════════════════════════════════════════════════
# Auth / IDOR / 404 anti-leak
# ════════════════════════════════════════════════════════════════════


class TestImpactAuthAndIdor:
    def test_no_token_returns_401_or_403(self, client, seeded_item):
        r = client.get(f"{ITEMS}/{seeded_item}/impact")
        assert r.status_code in (401, 403)

    def test_viewer_can_read_impact(self, client, viewer_token, seeded_item):
        r = client.get(f"{ITEMS}/{seeded_item}/impact", headers=_h(viewer_token))
        assert r.status_code == 200

    def test_user_can_read_impact(self, client, user_token, seeded_item):
        r = client.get(f"{ITEMS}/{seeded_item}/impact", headers=_h(user_token))
        assert r.status_code == 200

    def test_admin_can_read_impact(self, client, admin_token, seeded_item):
        r = client.get(f"{ITEMS}/{seeded_item}/impact", headers=_h(admin_token))
        assert r.status_code == 200

    def test_nonexistent_item_returns_404(self, client, user_token):
        r = client.get(f"{ITEMS}/{uuid.uuid4()}/impact", headers=_h(user_token))
        assert r.status_code == 404
        assert r.json()["detail"]["code"] == "ITEM_NOT_FOUND"

    def test_cross_org_item_returns_404_no_leak(self, client, user_token_org_2, seeded_item_org_1):
        """M2-5.10.bis clôture (audit code-reviewer P1-2) — IDOR cross-org.

        Org 2 ne doit jamais voir l'impact d'un item de l'org 1, et la
        réponse doit être 404 ITEM_NOT_FOUND (pas 403 — pas de fuite
        d'existence, cohérent IS3 anti-leak ADR-027).
        """
        r = client.get(f"{ITEMS}/{seeded_item_org_1}/impact", headers=_h(user_token_org_2))
        assert r.status_code == 404
        assert r.json()["detail"]["code"] == "ITEM_NOT_FOUND"


# ════════════════════════════════════════════════════════════════════
# Réponse structurée — 4 quadrants + has_data
# ════════════════════════════════════════════════════════════════════


class TestImpactResponseShape:
    def test_empty_impact_returns_4_null_quadrants(self, client, user_token, seeded_item):
        """Item sans impact_payload → 4 quadrants à null + has_data=False."""
        r = client.get(f"{ITEMS}/{seeded_item}/impact", headers=_h(user_token))
        assert r.status_code == 200
        body = r.json()
        assert body["item_id"] == seeded_item
        assert body["period"] == "12m"
        for key in ("estimated", "at_risk", "secured", "realized"):
            assert key in body
            assert body[key]["value_eur"] is None
            assert body[key]["detail"] is None
        assert body["has_data"] is False

    def test_populated_impact_returns_values(self, app_client, user_token):
        """Item avec impact_payload → quadrants lus + has_data=True."""
        client, session_local = app_client
        item_id = uuid.uuid4()
        db = session_local()
        try:
            db.add(
                ActionCenterItem(
                    id=item_id,
                    organisation_id=1,
                    kind="action",
                    title="Audit SMÉ Toulouse",
                    priority_bracket="P0",
                    priority_score=88.0,
                    impact_payload={
                        "estimated": {
                            "value_eur": 49000,
                            "detail": "gain si audit + plan pilotage CTA mis en œuvre",
                            "formula": "320 MWh × 153 €/MWh",
                            "source": "Modèle V4 · scénario B",
                        },
                        "at_risk": {
                            "value_eur": 7500,
                            "detail": "pénalité OPERAT si non-respect cycle SMÉ",
                            "formula": "15 €/m² × 500 m²",
                            "source": "Décret 2014-1393 art. 5",
                        },
                    },
                )
            )
            db.commit()
        finally:
            db.close()

        r = client.get(f"{ITEMS}/{item_id}/impact", headers=_h(user_token))
        assert r.status_code == 200
        body = r.json()
        assert body["has_data"] is True
        # Quadrants peuplés.
        assert body["estimated"]["value_eur"] == 49000.0
        assert body["estimated"]["formula"] == "320 MWh × 153 €/MWh"
        assert body["estimated"]["source"] == "Modèle V4 · scénario B"
        assert body["at_risk"]["value_eur"] == 7500.0
        # Quadrants absents du payload → null défensif.
        assert body["secured"]["value_eur"] is None
        assert body["realized"]["value_eur"] is None

    def test_partial_impact_one_dimension(self, app_client, user_token):
        """Une seule dimension peuplée suffit à activer has_data=True."""
        client, session_local = app_client
        item_id = uuid.uuid4()
        db = session_local()
        try:
            db.add(
                ActionCenterItem(
                    id=item_id,
                    organisation_id=1,
                    kind="recommendation",
                    title="Opportunité APER",
                    priority_bracket="P1",
                    priority_score=68.0,
                    impact_payload={"estimated": {"value_eur": 14000}},
                )
            )
            db.commit()
        finally:
            db.close()

        r = client.get(f"{ITEMS}/{item_id}/impact", headers=_h(user_token))
        assert r.status_code == 200
        body = r.json()
        assert body["has_data"] is True
        assert body["estimated"]["value_eur"] == 14000.0
        # Autres dimensions à null.
        assert body["at_risk"]["value_eur"] is None
        assert body["secured"]["value_eur"] is None
        assert body["realized"]["value_eur"] is None

    def test_legacy_impact_dimension_exposed_as_dominant(self, app_client, user_token):
        """Le champ legacy `impact_dimension` est exposé via `dominant_dimension`."""
        client, session_local = app_client
        item_id = uuid.uuid4()
        db = session_local()
        try:
            db.add(
                ActionCenterItem(
                    id=item_id,
                    organisation_id=1,
                    kind="anomaly",
                    title="X",
                    priority_bracket="P2",
                    priority_score=50.0,
                    impact_dimension="at_risk",
                )
            )
            db.commit()
        finally:
            db.close()

        r = client.get(f"{ITEMS}/{item_id}/impact", headers=_h(user_token))
        assert r.status_code == 200
        assert r.json()["dominant_dimension"] == "at_risk"


# ════════════════════════════════════════════════════════════════════
# Cardinal doctrine — aucun calcul dérivé MV3
# ════════════════════════════════════════════════════════════════════


class TestImpactDoctrine:
    def test_no_derived_value_from_priority_score(self, app_client, user_token):
        """Cardinal : un item P0/score=92 sans payload → value_eur=null partout.

        Le service ne dérive PAS une valeur € depuis priority_bracket ou
        priority_score (cf. doctrine v0.3 §8.5 : un chiffre € sans source
        et sans formule est un chiffre menteur).
        """
        client, session_local = app_client
        item_id = uuid.uuid4()
        db = session_local()
        try:
            db.add(
                ActionCenterItem(
                    id=item_id,
                    organisation_id=1,
                    kind="anomaly",
                    title="P0 high-score sans impact",
                    priority_bracket="P0",
                    priority_score=92.0,
                )
            )
            db.commit()
        finally:
            db.close()

        r = client.get(f"{ITEMS}/{item_id}/impact", headers=_h(user_token))
        assert r.status_code == 200
        body = r.json()
        for key in ("estimated", "at_risk", "secured", "realized"):
            assert body[key]["value_eur"] is None, f"Aucune valeur ne doit être inventée — {key} doit rester null"
        assert body["has_data"] is False

    def test_invalid_value_eur_coerced_to_null(self, app_client, user_token):
        """Cast défensif : string vide / NaN / non-numérique → null."""
        client, session_local = app_client
        item_id = uuid.uuid4()
        db = session_local()
        try:
            db.add(
                ActionCenterItem(
                    id=item_id,
                    organisation_id=1,
                    kind="anomaly",
                    title="bad payload",
                    priority_bracket="P2",
                    priority_score=50.0,
                    impact_payload={
                        "estimated": {"value_eur": ""},
                        "at_risk": {"value_eur": "not-a-number"},
                        "secured": {"value_eur": None},
                    },
                )
            )
            db.commit()
        finally:
            db.close()

        r = client.get(f"{ITEMS}/{item_id}/impact", headers=_h(user_token))
        assert r.status_code == 200
        body = r.json()
        assert body["estimated"]["value_eur"] is None
        assert body["at_risk"]["value_eur"] is None
        assert body["secured"]["value_eur"] is None
        assert body["has_data"] is False
