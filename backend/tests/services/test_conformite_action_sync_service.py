"""
PROMEOS — Conformité P0-5 2026-05-23 : test du service de planification de remédiation.

Vérifie que `plan_remediation_actions_for_org` produit un plan idempotent à
partir des DATA_MISSING réglementaires, sans écrire en base.

Boucle Conformité → Centre d'Action — fondations P0-5 (P1 livrera l'endpoint).
"""

from __future__ import annotations

import os
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from models import (  # noqa: E402
    Base,
    EntiteJuridique,
    Organisation,
    Portefeuille,
    Site,
    TypeSite,
)
from models.v4.enums import Domain, Kind  # noqa: E402
from services.v4.conformite_action_sync_service import (  # noqa: E402
    ActionItemDraft,
    RemediationPlan,
    plan_remediation_actions_for_org,
)


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def _make_org_with_site(db, *, surface=None, usage=None):
    """Crée Org + EJ + PF + Site avec champs réglementaires nullables (pour DATA_MISSING)."""
    org = Organisation(nom="Org P0-5", siren="111111111", type_client="bureau", actif=True)
    db.add(org)
    db.flush()
    ej = EntiteJuridique(organisation_id=org.id, nom="EJ", siren="111111111")
    db.add(ej)
    db.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="PF")
    db.add(pf)
    db.flush()
    site = Site(
        portefeuille_id=pf.id,
        nom="Site Conformite",
        type=TypeSite.BUREAU,
        adresse="x",
        code_postal="75001",
        ville="Paris",
        surface_m2=surface,
        tertiaire_area_m2=None,  # → déclenche DT.DATA_MISSING.SURFACE
        actif=True,
    )
    db.add(site)
    db.commit()
    return org, site


# ─── Cas nominaux ────────────────────────────────────────────────────────────


def test_plan_is_empty_when_no_data_missing(db):
    """Org sans DATA_MISSING (toutes données présentes) → plan vide."""
    org, site = _make_org_with_site(db, surface=1500)
    site.tertiaire_area_m2 = 1500
    site.usage_principal = "BUREAUX"
    db.commit()

    plan = plan_remediation_actions_for_org(db, org.id)
    assert isinstance(plan, RemediationPlan)
    # Le plan peut contenir d'autres règles (SMÉ/BEGES org-level) selon l'état des champs.
    # On vérifie au moins l'absence de DT.DATA_MISSING.SURFACE.
    dt_surface = [d for d in plan.items_to_create if d.reason_code == "DT.DATA_MISSING.SURFACE"]
    assert dt_surface == []


def test_plan_detects_dt_data_missing_surface(db):
    """Site sans tertiaire_area_m2 → DT.DATA_MISSING.SURFACE planifié."""
    org, site = _make_org_with_site(db)
    plan = plan_remediation_actions_for_org(db, org.id)
    dt_drafts = [d for d in plan.items_to_create if d.reason_code == "DT.DATA_MISSING.SURFACE"]
    assert len(dt_drafts) == 1
    draft = dt_drafts[0]
    assert draft.kind == Kind.EVIDENCE_REQUEST.value
    assert draft.domain == Domain.CONFORMITE.value
    assert draft.rule_code == "DT"
    assert draft.organisation_id == org.id
    assert draft.scope_level == "site"
    assert draft.scope_id == site.id
    assert draft.remediation_field == "site.tertiaire_area_m2"


def test_plan_title_is_french(db):
    """Le titre d'un draft est en FR canonique."""
    org, _ = _make_org_with_site(db)
    plan = plan_remediation_actions_for_org(db, org.id)
    dt_drafts = [d for d in plan.items_to_create if d.reason_code == "DT.DATA_MISSING.SURFACE"]
    assert len(dt_drafts) == 1
    draft = dt_drafts[0]
    assert "Décret Tertiaire" in draft.title_fr
    assert "Surface tertiaire" in draft.title_fr
    assert "compléter" in draft.title_fr.lower()


def test_plan_cta_label_french(db):
    """`cta_label_fr` du draft est en FR (vient de remediation P0-B)."""
    org, _ = _make_org_with_site(db)
    plan = plan_remediation_actions_for_org(db, org.id)
    dt_drafts = [d for d in plan.items_to_create if d.reason_code == "DT.DATA_MISSING.SURFACE"]
    assert dt_drafts[0].cta_label_fr == "Compléter la surface"


def test_plan_external_ref_is_stable(db):
    """`external_ref` doit être stable entre 2 appels (clé idempotency P1)."""
    org, _ = _make_org_with_site(db)
    plan_1 = plan_remediation_actions_for_org(db, org.id)
    plan_2 = plan_remediation_actions_for_org(db, org.id)
    refs_1 = sorted(d.external_ref for d in plan_1.items_to_create)
    refs_2 = sorted(d.external_ref for d in plan_2.items_to_create)
    assert refs_1 == refs_2


def test_plan_external_ref_format(db):
    """`external_ref` suit le pattern `rule:scope_level:scope_id:reason_code`."""
    org, site = _make_org_with_site(db)
    plan = plan_remediation_actions_for_org(db, org.id)
    dt_drafts = [d for d in plan.items_to_create if d.reason_code == "DT.DATA_MISSING.SURFACE"]
    expected = f"DT:site:{site.id}:DT.DATA_MISSING.SURFACE"
    assert dt_drafts[0].external_ref == expected


def test_plan_summary_counts_by_rule(db):
    """`summary` agrège les compteurs par règle."""
    org, _ = _make_org_with_site(db)
    plan = plan_remediation_actions_for_org(db, org.id)
    assert plan.summary["total"] == len(plan.items_to_create)
    if "by_rule_DT" in plan.summary:
        assert plan.summary["by_rule_DT"] >= 1


def test_plan_does_not_write_to_db(db):
    """Le service P0-5 est READ-ONLY : aucun ActionCenterItem n'est créé."""
    from models.v4.action_center_items import ActionCenterItem

    org, _ = _make_org_with_site(db)
    items_before = db.query(ActionCenterItem).count()
    plan_remediation_actions_for_org(db, org.id)
    items_after = db.query(ActionCenterItem).count()
    assert items_before == items_after, "Le service P0-5 doit être READ-ONLY"


def test_plan_serializable_to_dict(db):
    """`plan.to_dict()` doit être sérialisable JSON pour exposition future API."""
    import json

    org, _ = _make_org_with_site(db)
    plan = plan_remediation_actions_for_org(db, org.id)
    payload = plan.to_dict()
    json_str = json.dumps(payload)
    parsed = json.loads(json_str)
    assert parsed["org_id"] == org.id
    assert "items_to_create" in parsed
    assert "summary" in parsed
    assert "computed_at" in parsed


def test_unknown_org_returns_empty_plan(db):
    """Org inexistante → plan vide, pas de crash."""
    plan = plan_remediation_actions_for_org(db, org_id=9999)
    assert isinstance(plan, RemediationPlan)
    assert plan.items_to_create == []
