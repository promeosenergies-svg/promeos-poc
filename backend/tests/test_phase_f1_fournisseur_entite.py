"""
PROMEOS — Phase F1 (ADR-F-01) : tests cardinaux Fournisseur entité.

15 tests T-FOUR-01 → T-FOUR-15 :
- Création canonique + privé (T-FOUR-01/02)
- Validators stricts SIREN/TVA/email (T-FOUR-03/04/05)
- UniqueConstraint canonique + privé (T-FOUR-06/07/08)
- IDOR cross-tenant (T-FOUR-09)
- Backfill idempotent + variantes (T-FOUR-10/11)
- Endpoints REST UNION + refus mutation canonique (T-FOUR-12/13)
- Source-guard miroir transitoire (T-FOUR-14)
- Migration Alembic up/down (T-FOUR-15)
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import get_db
from main import app
from models import (
    Base,
    EnergyContract,
    Fournisseur,
    Organisation,
    TypeFournitureEnum,
)
from models.enums import BillingEnergyType


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def client(db):
    def _override():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


def _seed_two_orgs(db):
    org_a = Organisation(nom="Org Alpha", type_client="bureau", actif=True, siren="111111111")
    org_b = Organisation(nom="Org Bravo", type_client="industrie", actif=True, siren="222222222")
    db.add_all([org_a, org_b])
    db.commit()
    return org_a, org_b


# ─── T-FOUR-01 / 02 : Création canonique + privé ────────────────────────────


def test_t_four_01_creation_canonique(db):
    """T-FOUR-01 : Fournisseur canonique (organisation_id=NULL)."""
    f = Fournisseur(
        nom="EDF",
        siren="552081317",
        type_fourniture=TypeFournitureEnum.MULTI,
    )
    db.add(f)
    db.commit()
    assert f.id is not None
    assert f.organisation_id is None
    assert f.is_canonique() is True


def test_t_four_02_creation_privee(db):
    """T-FOUR-02 : Fournisseur privé d'une organisation."""
    org_a, _ = _seed_two_orgs(db)
    f = Fournisseur(
        organisation_id=org_a.id,
        nom="ELD Régionale",
        siren="123456789",
        type_fourniture=TypeFournitureEnum.GAZ,
    )
    db.add(f)
    db.commit()
    assert f.organisation_id == org_a.id
    assert f.is_canonique() is False


# ─── T-FOUR-03 / 04 / 05 : Validators stricts ───────────────────────────────


def test_t_four_03_validator_siren_invalide():
    """T-FOUR-03 : SIREN 8 chiffres → ValueError."""
    f = Fournisseur(nom="X", type_fourniture=TypeFournitureEnum.ELEC)
    with pytest.raises(ValueError, match="siren"):
        f.siren = "12345678"


def test_t_four_04_validator_tva_invalide():
    """T-FOUR-04 : TVA `FRXX` (mauvais format) → ValueError."""
    f = Fournisseur(nom="X", type_fourniture=TypeFournitureEnum.ELEC)
    with pytest.raises(ValueError, match="tva_intra"):
        f.tva_intra = "FRXX"


def test_t_four_05_validator_email_invalide():
    """T-FOUR-05 : Email malformé → ValueError."""
    f = Fournisseur(nom="X", type_fourniture=TypeFournitureEnum.ELEC)
    with pytest.raises(ValueError, match="contact_email"):
        f.contact_email = "bad-email-no-at"


# ─── T-FOUR-06 / 07 / 08 : UniqueConstraint SIREN ───────────────────────────


def test_t_four_06_unique_siren_canonique(db):
    """T-FOUR-06 : 2 canoniques même SIREN → IntegrityError."""
    db.add(Fournisseur(nom="EDF", siren="552081317", type_fourniture=TypeFournitureEnum.MULTI))
    db.commit()
    db.add(Fournisseur(nom="EDF Bis", siren="552081317", type_fourniture=TypeFournitureEnum.ELEC))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_t_four_07_unique_siren_meme_org(db):
    """T-FOUR-07 : 2 fournisseurs privés même org même SIREN → IntegrityError."""
    org_a, _ = _seed_two_orgs(db)
    db.add(Fournisseur(organisation_id=org_a.id, nom="X1", siren="123456789", type_fourniture=TypeFournitureEnum.ELEC))
    db.commit()
    db.add(Fournisseur(organisation_id=org_a.id, nom="X2", siren="123456789", type_fourniture=TypeFournitureEnum.GAZ))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_t_four_08_unique_siren_cross_org_autorise(db):
    """T-FOUR-08 : SIREN identique 2 orgs privées → autorisé."""
    org_a, org_b = _seed_two_orgs(db)
    db.add(
        Fournisseur(organisation_id=org_a.id, nom="ELD A", siren="123456789", type_fourniture=TypeFournitureEnum.GAZ)
    )
    db.add(
        Fournisseur(organisation_id=org_b.id, nom="ELD B", siren="123456789", type_fourniture=TypeFournitureEnum.GAZ)
    )
    db.commit()
    count = db.query(Fournisseur).filter(Fournisseur.siren == "123456789").count()
    assert count == 2


# ─── T-FOUR-09 : IDOR cross-tenant ──────────────────────────────────────────


def test_t_four_09_idor_org_a_voit_pas_fournisseur_prive_org_b(client, db):
    """T-FOUR-09 : Org A ne voit pas fournisseurs privés Org B (canoniques OK)."""
    org_a, org_b = _seed_two_orgs(db)
    # 1 canonique partagé
    db.add(Fournisseur(nom="EDF", siren="552081317", type_fourniture=TypeFournitureEnum.MULTI))
    # 1 privé Bravo
    db.add(
        Fournisseur(
            organisation_id=org_b.id,
            nom="ELD Bravo",
            siren="999999999",
            type_fourniture=TypeFournitureEnum.GAZ,
        )
    )
    db.commit()

    r = client.get("/api/fournisseurs", headers={"X-Org-Id": str(org_a.id)})
    assert r.status_code == 200
    noms = [f["nom"] for f in r.json()["fournisseurs"]]
    assert "EDF" in noms  # canonique visible
    assert "ELD Bravo" not in noms  # privé Bravo invisible pour Alpha


# ─── T-FOUR-10 / 11 : Backfill idempotent + variantes ───────────────────────


def test_t_four_10_backfill_idempotent(db):
    """T-FOUR-10 : 2× exécution = même résultat."""
    from scripts.backfill_fournisseur_id import backfill_fournisseur_id
    from services.demo_seed.fournisseurs_canoniques import seed_fournisseurs_canoniques
    from models import Site, EntiteJuridique, Portefeuille
    from models.enums import TypeSite

    seed_fournisseurs_canoniques(db)
    org_a, _ = _seed_two_orgs(db)
    ej = EntiteJuridique(organisation_id=org_a.id, nom="EJ", siren=org_a.siren)
    db.add(ej)
    db.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="PF")
    db.add(pf)
    db.flush()
    site = Site(portefeuille_id=pf.id, nom="S", type=TypeSite.BUREAU, actif=True)
    db.add(site)
    db.flush()

    contract = EnergyContract(site_id=site.id, energy_type=BillingEnergyType.ELEC, supplier_name="EDF")
    db.add(contract)
    db.commit()

    r1 = backfill_fournisseur_id(db)
    r2 = backfill_fournisseur_id(db)
    assert r1["updated"] == 1
    assert r2["updated"] == 0  # idempotent


def test_t_four_11_backfill_variantes_orthographiques(db):
    """T-FOUR-11 : `EDF` + `E.D.F.` → même fournisseur_id."""
    from scripts.backfill_fournisseur_id import backfill_fournisseur_id
    from services.demo_seed.fournisseurs_canoniques import seed_fournisseurs_canoniques
    from models import Site, EntiteJuridique, Portefeuille
    from models.enums import TypeSite

    seed_fournisseurs_canoniques(db)
    org_a, _ = _seed_two_orgs(db)
    ej = EntiteJuridique(organisation_id=org_a.id, nom="EJ", siren=org_a.siren)
    db.add(ej)
    db.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="PF")
    db.add(pf)
    db.flush()
    site = Site(portefeuille_id=pf.id, nom="S", type=TypeSite.BUREAU, actif=True)
    db.add(site)
    db.flush()

    c1 = EnergyContract(site_id=site.id, energy_type=BillingEnergyType.ELEC, supplier_name="EDF")
    c2 = EnergyContract(site_id=site.id, energy_type=BillingEnergyType.GAZ, supplier_name="E.D.F.")
    db.add_all([c1, c2])
    db.commit()

    backfill_fournisseur_id(db)
    db.refresh(c1)
    db.refresh(c2)
    assert c1.fournisseur_id is not None
    assert c1.fournisseur_id == c2.fournisseur_id


# ─── T-FOUR-12 / 13 : Endpoints REST ────────────────────────────────────────


def test_t_four_12_endpoint_list_union_canoniques_prives(client, db):
    """T-FOUR-12 : GET /api/fournisseurs retourne canoniques + privés scope."""
    org_a, _ = _seed_two_orgs(db)
    db.add(Fournisseur(nom="EDF Canonique", siren="552081317", type_fourniture=TypeFournitureEnum.MULTI))
    db.add(
        Fournisseur(
            organisation_id=org_a.id,
            nom="ELD Privé Alpha",
            siren="123456789",
            type_fourniture=TypeFournitureEnum.GAZ,
        )
    )
    db.commit()

    r = client.get("/api/fournisseurs", headers={"X-Org-Id": str(org_a.id)})
    assert r.status_code == 200
    noms = sorted([f["nom"] for f in r.json()["fournisseurs"]])
    assert noms == ["EDF Canonique", "ELD Privé Alpha"]


def test_t_four_13_endpoint_refuse_mutation_canonique(client, db):
    """T-FOUR-13 : Endpoint refuse mutation fournisseur canonique par tenant (403)."""
    org_a, _ = _seed_two_orgs(db)
    f = Fournisseur(nom="EDF", siren="552081317", type_fourniture=TypeFournitureEnum.MULTI)
    db.add(f)
    db.commit()

    r = client.patch(
        f"/api/fournisseurs/{f.id}",
        json={"nom": "EDF Hacked"},
        headers={"X-Org-Id": str(org_a.id)},
    )
    assert r.status_code == 403
    assert "FOURNISSEUR_CANONIQUE_READ_ONLY" in str(r.json())


# ─── T-FOUR-13bis : PII masking canoniques (Phase F1 P1 fix code-reviewer) ──


def test_t_four_13bis_pii_masque_sur_canoniques(client, db):
    """Phase F1 P1 fix : contact_email + signataire_email masqués sur canoniques.

    Pattern Pilier 13 ADR-016 PII SoT — exposition uniquement au propriétaire.
    """
    org_a, _ = _seed_two_orgs(db)
    f_canon = Fournisseur(
        nom="EDF",
        siren="552081317",
        type_fourniture=TypeFournitureEnum.MULTI,
        contact_email="contact@edf.fr",
        signataire_email="signature@edf.fr",
    )
    db.add(f_canon)
    db.commit()

    r = client.get(f"/api/fournisseurs/{f_canon.id}", headers={"X-Org-Id": str(org_a.id)})
    data = r.json()
    assert data["nom"] == "EDF"
    assert data["contact_email"] is None  # masqué (canonique vu par tenant)
    assert data["signataire_email"] is None  # masqué
    assert data["site_web"] is None  # cohérent : public OK même si non set


def test_t_four_13ter_pii_visible_sur_prive_owner(client, db):
    """PII visible uniquement au propriétaire d'un fournisseur privé."""
    org_a, _ = _seed_two_orgs(db)
    f_prive = Fournisseur(
        organisation_id=org_a.id,
        nom="ELD Privé",
        siren="123456789",
        type_fourniture=TypeFournitureEnum.GAZ,
        contact_email="prive@eld.fr",
        signataire_email="sign@eld.fr",
    )
    db.add(f_prive)
    db.commit()

    r = client.get(f"/api/fournisseurs/{f_prive.id}", headers={"X-Org-Id": str(org_a.id)})
    data = r.json()
    assert data["contact_email"] == "prive@eld.fr"  # visible owner
    assert data["signataire_email"] == "sign@eld.fr"  # visible owner


# ─── T-FOUR-14 : Source-guard miroir transitoire ────────────────────────────


def test_t_four_14_supplier_name_preserved_post_phase_f1():
    """T-FOUR-14 : `supplier_name` String coexiste avec `fournisseur_id` Phase F1.

    Vérifie que le miroir transitoire ADR-F-01 D2 est intact :
    `supplier_name` reste NOT NULL pour permettre backfill progressif sans casse.
    Hard-cut report Phase F2 ADR-F-04 séparé.
    """
    from sqlalchemy import inspect

    from database import engine

    cols = {c["name"]: c for c in inspect(engine).get_columns("energy_contracts")}
    assert "supplier_name" in cols, "supplier_name DROP interdit Phase F1"
    assert "fournisseur_id" in cols, "fournisseur_id FK manquant Phase F1"
    assert cols["supplier_name"]["nullable"] is False  # encore obligatoire
    assert cols["fournisseur_id"]["nullable"] is True  # nullable (miroir transitoire)


# ─── T-FOUR-15 : Migration Alembic up/down ──────────────────────────────────


def test_t_four_15_migration_alembic_present():
    """T-FOUR-15 : Migration Alembic Phase F1 enregistrée (up + down idempotent)."""
    from pathlib import Path

    backend_root = Path(__file__).resolve().parent.parent
    migration = backend_root / "alembic" / "versions" / "a1b2c3d4e5f6_phase_f1_fournisseur_entite_normalisation.py"
    assert migration.exists()
    src = migration.read_text(encoding="utf-8")
    assert 'revision: str = "a1b2c3d4e5f6"' in src
    assert "down_revision" in src and "17c5ab8161bf" in src
    # Idempotent : check tables/columns existence avant create/add
    assert 'if "fournisseurs" not in existing_tables' in src
    assert 'if "fournisseur_id" not in contract_cols' in src
    # Anti-DROP discipline : downgrade ne contient PAS d'opération drop_column sur supplier_name
    downgrade_src = src.split("def downgrade")[1]
    assert 'drop_column("supplier_name"' not in downgrade_src
    assert "op.drop_column('supplier_name'" not in downgrade_src
