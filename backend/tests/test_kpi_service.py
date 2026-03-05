"""
Tests — KPI Service centralized (Playbook 2.2).
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.base import Base
from models import Organisation, EntiteJuridique, Portefeuille, Site, StatutConformite
from services.kpi_service import KpiService, KpiScope, KpiResult, _cache


@pytest.fixture()
def db():
    """In-memory SQLite with seed data."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed minimal data
    org = Organisation(id=1, nom="Test Org", siren="123456789", type_client="tertiaire")
    session.add(org)
    session.flush()

    ej = EntiteJuridique(id=1, nom="EJ Test", siren="123456789", siret="12345678900001", organisation_id=1)
    session.add(ej)
    session.flush()

    pf = Portefeuille(id=1, nom="PF Test", entite_juridique_id=1)
    session.add(pf)
    session.flush()

    sites = [
        Site(id=1, nom="Site A", type="bureau", portefeuille_id=1, actif=True, surface_m2=1000,
             risque_financier_euro=5000, avancement_decret_pct=80,
             statut_decret_tertiaire=StatutConformite.CONFORME),
        Site(id=2, nom="Site B", type="commerce", portefeuille_id=1, actif=True, surface_m2=2000,
             risque_financier_euro=10000, avancement_decret_pct=60,
             statut_decret_tertiaire=StatutConformite.NON_CONFORME),
        Site(id=3, nom="Site C", type="bureau", portefeuille_id=1, actif=True, surface_m2=500,
             risque_financier_euro=0, avancement_decret_pct=100,
             statut_decret_tertiaire=StatutConformite.CONFORME),
    ]
    session.add_all(sites)
    session.commit()

    _cache.clear()
    yield session
    session.close()
    engine.dispose()


class TestKpiServiceFinancialRisk:
    def test_org_total(self, db):
        svc = KpiService(db)
        result = svc.get_financial_risk_eur(KpiScope(org_id=1))
        assert result.value == 15000.0
        assert result.unit == "EUR"
        assert result.confidence == "high"

    def test_single_site(self, db):
        svc = KpiService(db)
        result = svc.get_financial_risk_eur(KpiScope(site_id=2))
        assert result.value == 10000.0

    def test_sum_sites_equals_org(self, db):
        """Sum of individual site KPIs should equal org-level KPI."""
        svc = KpiService(db)
        org_total = svc.get_financial_risk_eur(KpiScope(org_id=1)).value
        site_sum = sum(
            svc.get_financial_risk_eur(KpiScope(site_id=sid)).value
            for sid in [1, 2, 3]
        )
        assert abs(org_total - site_sum) < 0.01


class TestKpiServiceCompliance:
    def test_compliance_score(self, db):
        svc = KpiService(db)
        result = svc.get_compliance_score(KpiScope(org_id=1))
        # 2 out of 3 sites CONFORME = 66.7%
        assert abs(result.value - 66.7) < 0.1
        assert result.unit == "%"

    def test_empty_scope(self, db):
        svc = KpiService(db)
        result = svc.get_compliance_score(KpiScope(org_id=999))
        assert result.value == 0.0
        assert result.confidence == "low"


class TestKpiServiceSurface:
    def test_total_surface(self, db):
        svc = KpiService(db)
        result = svc.get_total_surface_m2(KpiScope(org_id=1))
        assert result.value == 3500.0
        assert result.unit == "m²"


class TestKpiServiceAvancement:
    def test_avg_avancement(self, db):
        svc = KpiService(db)
        result = svc.get_avancement_decret_pct(KpiScope(org_id=1))
        assert abs(result.value - 80.0) < 0.1  # (80 + 60 + 100) / 3 = 80


class TestKpiCaching:
    def test_same_result_on_second_call(self, db):
        """Cache should return same result."""
        svc = KpiService(db)
        r1 = svc.get_financial_risk_eur(KpiScope(org_id=1))
        r2 = svc.get_financial_risk_eur(KpiScope(org_id=1))
        assert r1.value == r2.value


class TestKpiResult:
    def test_result_has_all_fields(self, db):
        """KpiResult should have value, unit, source, formula, confidence."""
        svc = KpiService(db)
        result = svc.get_financial_risk_eur(KpiScope(org_id=1))
        assert isinstance(result, KpiResult)
        assert result.value is not None
        assert result.unit is not None
        assert result.source is not None
        assert result.formula is not None
        assert result.confidence in ("high", "medium", "low")
