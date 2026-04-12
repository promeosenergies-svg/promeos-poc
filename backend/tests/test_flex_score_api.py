"""
Tests API des endpoints flex_score.py.
Verifie : montage router, reponses 200, coherence referentiel.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


class TestFlexScoreRouterMount:
    """Verifier que le router flex_score est monte dans main.py."""

    def test_get_usages_200(self, app_client):
        """GET /api/flex/score/usages -> 200."""
        client, _ = app_client
        resp = client.get("/api/flex/score/usages")
        assert resp.status_code == 200
        data = resp.json()
        assert data["n_usages"] == 15
        assert len(data["usages"]) == 15

    def test_prix_signal_neutre(self, app_client):
        """GET /api/flex/score/prix-signal?prix_spot_eur_mwh=45 -> signal NEUTRE."""
        client, _ = app_client
        resp = client.get("/api/flex/score/prix-signal", params={"prix_spot_eur_mwh": 45})
        assert resp.status_code == 200
        data = resp.json()
        assert data["signal"] == "NEUTRE"
        assert "usages_cibles" in data

    def test_prix_signal_negatif(self, app_client):
        """GET /api/flex/score/prix-signal?prix_spot_eur_mwh=-15 -> PRIX_NEGATIF."""
        client, _ = app_client
        resp = client.get("/api/flex/score/prix-signal", params={"prix_spot_eur_mwh": -15})
        assert resp.status_code == 200
        data = resp.json()
        assert data["signal"] == "PRIX_NEGATIF"
        assert data["modulation_nebco"] == "ANTICIPATION"
        assert "BATTERIES" in data["usages_cibles"]

    def test_prix_signal_eleve(self, app_client):
        """GET /api/flex/score/prix-signal?prix_spot_eur_mwh=150 -> PRIX_ELEVE."""
        client, _ = app_client
        resp = client.get("/api/flex/score/prix-signal", params={"prix_spot_eur_mwh": 150})
        assert resp.status_code == 200
        data = resp.json()
        assert data["signal"] == "PRIX_ELEVE"
        assert data["modulation_nebco"] == "EFFACEMENT"


class TestFlexScoreSite:
    """Tests sur les endpoints site."""

    def test_site_inexistant_404(self, app_client):
        """Site inexistant -> 404."""
        client, _ = app_client
        resp = client.get("/api/flex/score/sites/99999")
        assert resp.status_code == 404

    def test_site_avec_seed(self, app_client):
        """Site cree via quick-create -> score retourne."""
        client, _ = app_client
        # Creer un site minimal
        client.post("/api/sites/quick-create", json={"nom": "TestFlex", "usage": "bureau"})
        resp = client.get("/api/flex/score/sites/1")
        assert resp.status_code == 200
        data = resp.json()
        assert "score_global_site" in data
        assert 0.0 <= data["score_global_site"] <= 1.0
        assert data["n_usages_evalues"] > 0

    def test_portfolio_vide_retourne_200(self, app_client):
        """Portfolio inexistant -> 404."""
        client, _ = app_client
        resp = client.get("/api/flex/score/portfolios/99999")
        assert resp.status_code == 404


class TestFlexScoreUsagesReferentiel:
    """Coherence du referentiel des 15 usages."""

    def test_irve_top_scoreur(self, app_client):
        """IRVE ou BATTERIES en tete du classement."""
        client, _ = app_client
        resp = client.get("/api/flex/score/usages")
        assert resp.status_code == 200
        usages = resp.json()["usages"]
        top = usages[0]
        assert top["score_global"] >= 0.80
        assert top["code"] in ("IRVE", "BATTERIES", "ECS")

    def test_process_continu_nogo(self, app_client):
        """PROCESS_CONTINU doit avoir nogo_nebco=True."""
        client, _ = app_client
        resp = client.get("/api/flex/score/usages")
        usages = resp.json()["usages"]
        continu = next(u for u in usages if u["code"] == "PROCESS_CONTINU")
        assert continu["nogo_nebco"] is True
        assert continu["score_global"] <= 0.35

    def test_15_usages_presents(self, app_client):
        """Exactement 15 usages."""
        client, _ = app_client
        resp = client.get("/api/flex/score/usages")
        assert resp.json()["n_usages"] == 15

    def test_p_max_filtre_nebco(self, app_client):
        """P_max=50 plafonne score NEBCO, P_max=500 ne plafonne pas."""
        client, _ = app_client
        resp_petit = client.get("/api/flex/score/usages", params={"P_max_kw": 50})
        resp_grand = client.get("/api/flex/score/usages", params={"P_max_kw": 500})
        usages_petit = {u["code"]: u for u in resp_petit.json()["usages"]}
        usages_grand = {u["code"]: u for u in resp_grand.json()["usages"]}
        # CVC_HVAC avec P_max petit devrait avoir un score NEBCO plus bas
        assert usages_petit["CVC_HVAC"]["nebco_score"] <= usages_grand["CVC_HVAC"]["nebco_score"]


class TestResolveArchetypeNoDefault:
    """
    Non-regression : tous les archetypes canoniques doivent etre resolvables
    depuis un NAF reel. Detecte les fallbacks DEFAULT silencieux.
    """

    # 1 NAF representatif par archetype canonique du moteur flex
    NAF_BY_ARCHETYPE = {
        "BUREAU_STANDARD": "6820A",
        "HOTEL_HEBERGEMENT": "5510Z",
        "ENSEIGNEMENT": "8520Z",
        "ENSEIGNEMENT_SUP": "8542Z",
        "SANTE": "8610Z",
        "RESTAURANT": "5610A",
        "COMMERCE_ALIMENTAIRE": "4711D",
        "LOGISTIQUE_SEC": "5210B",
        "LOGISTIQUE_FRIGO": "1013A",
        "DATA_CENTER": "6311Z",
        "INDUSTRIE_LEGERE": "2511Z",
        "SPORT_LOISIR": "9311Z",
        "COLLECTIVITE": "8411Z",
        "COPROPRIETE": "6832A",
    }

    def test_chaque_archetype_resolu_depuis_naf(self, app_client):
        """Aucun NAF de la table ne doit tomber en DEFAULT."""
        client, SessionLocal = app_client
        from models.site import Site
        from models.enums import TypeSite
        from routes.flex_score import _resolve_archetype

        db = SessionLocal()
        try:
            for expected, naf in self.NAF_BY_ARCHETYPE.items():
                site = Site(nom=f"Test {expected}", type=TypeSite.BUREAU, naf_code=naf, actif=True)
                db.add(site)
                db.commit()
                db.refresh(site)

                archetype = _resolve_archetype(db, site)
                assert archetype != "DEFAULT", f"NAF {naf} tombe en DEFAULT alors que {expected} etait attendu"
                # Verifier que l'archetype retourne est bien dans le referentiel flex
                from services.flex.flexibility_scoring_engine import ARCHETYPE_TO_USAGES

                assert archetype in ARCHETYPE_TO_USAGES, (
                    f"NAF {naf} -> archetype {archetype!r} absent de ARCHETYPE_TO_USAGES"
                )
        finally:
            db.close()

    def test_naf_format_dotted_resolu(self, app_client):
        """Les NAF au format DD.DDC (ex: '70.10Z') doivent etre resolus (strip dots avant slice)."""
        client, SessionLocal = app_client
        from models.site import Site
        from models.enums import TypeSite
        from routes.flex_score import _resolve_archetype

        db = SessionLocal()
        try:
            # 70.10Z (sieges sociaux) -> prefix 7010 -> BUREAU_STANDARD
            site = Site(nom="Dotted NAF", type=TypeSite.BUREAU, naf_code="70.10Z", actif=True)
            db.add(site)
            db.commit()
            db.refresh(site)

            archetype = _resolve_archetype(db, site)
            assert archetype == "BUREAU_STANDARD", f"NAF dotted '70.10Z' -> {archetype!r}, attendu 'BUREAU_STANDARD'"
        finally:
            db.close()

    def test_naf_inconnu_tombe_en_default(self, app_client):
        """Un NAF completement inconnu doit tomber en DEFAULT (comportement attendu)."""
        client, SessionLocal = app_client
        from models.site import Site
        from models.enums import TypeSite
        from routes.flex_score import _resolve_archetype

        db = SessionLocal()
        try:
            site = Site(nom="Site NAF bizarre", type=TypeSite.BUREAU, naf_code="0000Z", actif=True)
            db.add(site)
            db.commit()
            db.refresh(site)

            archetype = _resolve_archetype(db, site)
            assert archetype == "DEFAULT"
        finally:
            db.close()

    def test_kb_normalization_sante_hopital(self, app_client):
        """Normalisation KB : SANTE_HOPITAL (code KB) -> SANTE (code flex)."""
        from routes.flex_score import _normalize_archetype

        assert _normalize_archetype("SANTE_HOPITAL") == "SANTE"
        assert _normalize_archetype("DATACENTER") == "DATA_CENTER"
        assert _normalize_archetype("HOTEL_STANDARD") == "HOTEL_HEBERGEMENT"
        assert _normalize_archetype("RESTAURATION_SERVICE") == "RESTAURANT"
        assert _normalize_archetype("LOGISTIQUE_ENTREPOT") == "LOGISTIQUE_SEC"

    def test_kb_normalization_deja_canonique(self, app_client):
        """Un code deja canonique passe sans transformation."""
        from routes.flex_score import _normalize_archetype

        assert _normalize_archetype("BUREAU_STANDARD") == "BUREAU_STANDARD"
        assert _normalize_archetype("COLLECTIVITE") == "COLLECTIVITE"

    def test_kb_normalization_inconnu(self, app_client):
        """Un code totalement inconnu -> DEFAULT."""
        from routes.flex_score import _normalize_archetype

        assert _normalize_archetype("TOTALLY_UNKNOWN_CODE") == "DEFAULT"
        assert _normalize_archetype("") == "DEFAULT"
        assert _normalize_archetype(None) == "DEFAULT"
