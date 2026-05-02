"""PROMEOS — Tests endpoint GET /api/v1/navigation/badges.

Phase 2.A — P1.2 (audit navigation_audit_20260501.md §3.3 + §5).
Couvre : auth, org isolation, contrats du schema, mapping framework,
fenêtre purchase 90 j, fallbacks org sans data ou breakdown partiel.
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from unittest.mock import patch


def _seed_minimal_org(db, org_id: int, nom_suffix: str = "") -> int:
    """Crée Organisation + EntiteJuridique + Portefeuille + 1 Site actif.

    Génère un SIREN unique de 9 chiffres dérivé de org_id pour respecter
    la contrainte NOT NULL `entites_juridiques.siren` sans collision
    inter-tests.
    """
    from models import EntiteJuridique, Organisation, Portefeuille, Site
    from models.enums import TypeSite

    org = Organisation(id=org_id, nom=f"OrgTest{nom_suffix}")
    db.add(org)
    db.flush()
    ej = EntiteJuridique(
        nom=f"EJ{nom_suffix}",
        organisation_id=org_id,
        siren=f"{(900_000_000 + org_id) % 1_000_000_000:09d}",
    )
    db.add(ej)
    db.flush()
    pf = Portefeuille(nom=f"PF{nom_suffix}", entite_juridique_id=ej.id)
    db.add(pf)
    db.flush()
    site = Site(
        nom=f"Site{nom_suffix}",
        type=TypeSite.BUREAU,
        portefeuille_id=pf.id,
        actif=True,
        surface_m2=2000.0,
    )
    db.add(site)
    db.flush()
    db.commit()
    return site.id


# ── Tests fonctionnels ────────────────────────────────────────────────────


class TestNavigationBadgesEndpoint:
    def test_returns_200_authenticated(self, app_client):
        """Endpoint répond 200 avec NavBadgesResponse pour une org valide."""
        client, SessionLocal = app_client
        with SessionLocal() as db:
            _seed_minimal_org(db, org_id=42)

        r = client.get("/api/v1/navigation/badges", headers={"X-Org-Id": "42"})
        assert r.status_code == 200, r.text
        data = r.json()
        # 8 compteurs + 2 metadata
        assert set(data.keys()) >= {
            "energy_alerts",
            "compliance_alerts",
            "billing_anomalies",
            "purchase_deadlines",
            "action_center",
            "conformite_dt_progress",
            "conformite_bacs_progress",
            "conformite_aper_progress",
            "computed_at",
            "cache_ttl_seconds",
        }
        assert data["cache_ttl_seconds"] == 60

    def test_returns_401_when_demo_mode_off_and_no_token(self, app_client, monkeypatch):
        """DEMO_MODE=false sans token → 401 (raisé par get_optional_auth)."""
        # Re-import middleware/auth pour appliquer le monkeypatch.
        import middleware.auth as auth_mod

        monkeypatch.setattr(auth_mod, "DEMO_MODE", False)
        client, _ = app_client
        r = client.get("/api/v1/navigation/badges")
        assert r.status_code == 401, r.text

    def test_org_isolation(self, app_client):
        """Counts varient entre 2 orgs distinctes (isolation multi-tenant)."""
        client, SessionLocal = app_client
        with SessionLocal() as db:
            site_a = _seed_minimal_org(db, org_id=101, nom_suffix="A")
            _seed_minimal_org(db, org_id=102, nom_suffix="B")

            # Crée une anomalie billing uniquement pour l'org A.
            from models.billing_models import EnergyInvoice
            from models.enums import BillingInvoiceStatus

            invoice = EnergyInvoice(
                site_id=site_a,
                invoice_number="A-001",
                period_start=date.today() - timedelta(days=60),
                period_end=date.today() - timedelta(days=30),
                issue_date=date.today() - timedelta(days=20),
                total_eur=1234.0,
                status=BillingInvoiceStatus.ANOMALY,
            )
            db.add(invoice)
            db.commit()

        r_a = client.get("/api/v1/navigation/badges", headers={"X-Org-Id": "101"})
        r_b = client.get("/api/v1/navigation/badges", headers={"X-Org-Id": "102"})
        assert r_a.status_code == 200 and r_b.status_code == 200
        # Org A doit voir l'anomalie, Org B non.
        assert r_a.json()["billing_anomalies"] == 1
        assert r_b.json()["billing_anomalies"] == 0

    def test_all_counters_non_negative(self, app_client):
        """Pydantic ge=0 garantit l'absence de compteurs négatifs."""
        client, SessionLocal = app_client
        with SessionLocal() as db:
            _seed_minimal_org(db, org_id=200)

        r = client.get("/api/v1/navigation/badges", headers={"X-Org-Id": "200"})
        data = r.json()
        for key in (
            "energy_alerts",
            "compliance_alerts",
            "billing_anomalies",
            "purchase_deadlines",
            "action_center",
        ):
            assert data[key] >= 0, f"{key} doit être ≥ 0"

    def test_progress_fields_in_range_0_100(self, app_client):
        """Pydantic ge=0/le=100 garantit les bornes des progress."""
        client, SessionLocal = app_client
        with SessionLocal() as db:
            _seed_minimal_org(db, org_id=201)

        r = client.get("/api/v1/navigation/badges", headers={"X-Org-Id": "201"})
        data = r.json()
        for key in (
            "conformite_dt_progress",
            "conformite_bacs_progress",
            "conformite_aper_progress",
        ):
            assert 0.0 <= data[key] <= 100.0, f"{key}={data[key]} hors [0,100]"

    def test_empty_org_returns_zeros(self, app_client):
        """Org sans sites → tous compteurs = 0, progress = 0.0."""
        client, _ = app_client
        # Pas de seed : org_id=999 n'existe pas → counters = 0.
        r = client.get("/api/v1/navigation/badges", headers={"X-Org-Id": "999"})
        assert r.status_code == 200
        data = r.json()
        assert data["energy_alerts"] == 0
        assert data["billing_anomalies"] == 0
        assert data["purchase_deadlines"] == 0
        assert data["action_center"] == 0
        assert data["conformite_dt_progress"] == 0.0
        assert data["conformite_bacs_progress"] == 0.0
        assert data["conformite_aper_progress"] == 0.0


# ── Tests sur la logique de mapping & fenêtre ─────────────────────────────


class TestComplianceBreakdownMapping:
    def test_dt_mapped_from_tertiaire_operat(self, app_client):
        """compute_portfolio_compliance retourne 'tertiaire_operat' →
        exposé en 'conformite_dt_progress' (doctrine §11.3)."""
        client, SessionLocal = app_client
        with SessionLocal() as db:
            _seed_minimal_org(db, org_id=300)

        # Mock retour compute_portfolio_compliance (cible le service utilisé
        # par navigation_badges_service, pas le module d'origine).
        with patch(
            "services.navigation_badges_service.compute_portfolio_compliance",
            return_value={
                "breakdown_avg": {
                    "tertiaire_operat": 73.5,
                    "bacs": 41.2,
                    "aper": 88.0,
                }
            },
        ):
            r = client.get("/api/v1/navigation/badges", headers={"X-Org-Id": "300"})
        data = r.json()
        assert data["conformite_dt_progress"] == 73.5
        assert data["conformite_bacs_progress"] == 41.2
        assert data["conformite_aper_progress"] == 88.0

    def test_partial_breakdown_fallbacks_to_zero(self, app_client):
        """Si compute_portfolio_compliance omet une clé framework, le
        champ correspondant tombe à 0.0 (pas None, contrat NavBadgesResponse)."""
        client, SessionLocal = app_client
        with SessionLocal() as db:
            _seed_minimal_org(db, org_id=301)

        with patch(
            "services.navigation_badges_service.compute_portfolio_compliance",
            return_value={"breakdown_avg": {"bacs": 55.0}},
        ):
            r = client.get("/api/v1/navigation/badges", headers={"X-Org-Id": "301"})
        data = r.json()
        assert data["conformite_dt_progress"] == 0.0
        assert data["conformite_bacs_progress"] == 55.0
        assert data["conformite_aper_progress"] == 0.0


class TestPurchaseWindow:
    def test_purchase_window_uses_90_days(self, app_client):
        """PURCHASE_WINDOW_DAYS=90 : un contrat expirant à J+85 est compté,
        un contrat expirant à J+120 ne l'est pas (même org)."""
        from services.navigation_badges_service import PURCHASE_WINDOW_DAYS

        assert PURCHASE_WINDOW_DAYS == 90

        client, SessionLocal = app_client
        with SessionLocal() as db:
            site_id = _seed_minimal_org(db, org_id=400)

            from models.billing_models import EnergyContract
            from models.enums import BillingEnergyType

            today = date.today()
            db.add(
                EnergyContract(
                    site_id=site_id,
                    energy_type=BillingEnergyType.ELEC,
                    supplier_name="EDF",
                    start_date=today - timedelta(days=365),
                    end_date=today + timedelta(days=85),  # dans la fenêtre
                )
            )
            db.add(
                EnergyContract(
                    site_id=site_id,
                    energy_type=BillingEnergyType.GAZ,
                    supplier_name="Engie",
                    start_date=today - timedelta(days=200),
                    end_date=today + timedelta(days=120),  # hors fenêtre
                )
            )
            db.commit()

        r = client.get("/api/v1/navigation/badges", headers={"X-Org-Id": "400"})
        assert r.status_code == 200
        assert r.json()["purchase_deadlines"] == 1


# ── Source-guards minimaux co-localisés ────────────────────────────────────


class TestEndpointShape:
    def test_endpoint_registered_in_openapi(self, app_client):
        """OpenAPI expose /api/v1/navigation/badges (auto-doc disponible)."""
        client, _ = app_client
        r = client.get("/openapi.json")
        assert r.status_code == 200
        paths = r.json().get("paths", {})
        assert "/api/v1/navigation/badges" in paths
