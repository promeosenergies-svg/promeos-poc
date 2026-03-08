"""
PROMEOS — Tests Step 30 : Seed 3 EFA Tertiaire HELIOS
"""
import pytest
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base, Site, Batiment

BACKEND = os.path.join(os.path.dirname(__file__), "..")
SEED_PATH = os.path.join(BACKEND, "services", "demo_seed", "gen_tertiaire_efa.py")


# ═══════════════════════════════════════════════════════════════════════
# A. Source guard (no DB needed)
# ═══════════════════════════════════════════════════════════════════════

class TestSourceGuard:
    def test_file_exists(self):
        assert os.path.isfile(SEED_PATH), "gen_tertiaire_efa.py manquant"

    def test_importable(self):
        from services.demo_seed.gen_tertiaire_efa import seed_tertiaire_efa
        assert callable(seed_tertiaire_efa)

    def test_contains_3_efas(self):
        src = open(SEED_PATH, "r", encoding="utf-8").read()
        assert "Paris" in src
        assert "Nice" in src
        assert "Lyon" in src

    def test_idempotent_guard(self):
        src = open(SEED_PATH, "r", encoding="utf-8").read()
        assert "filter_by" in src, "Doit verifier l'existence avant creation"

    def test_orchestrator_wired(self):
        orch_path = os.path.join(BACKEND, "services", "demo_seed", "orchestrator.py")
        src = open(orch_path, "r", encoding="utf-8").read()
        assert "seed_tertiaire_efa" in src


# ═══════════════════════════════════════════════════════════════════════
# B. Seed integration tests (in-memory DB)
# ═══════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def seeded_db():
    """Seed HELIOS in an in-memory DB and return session."""
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()

    from services.demo_seed import SeedOrchestrator

    orch = SeedOrchestrator(session)
    orch.seed(pack="helios", size="S", rng_seed=42, days=30)

    yield session
    session.close()


class TestEfaCreation:
    def test_3_efas_created(self, seeded_db):
        """Au moins 3 EFA nommees (Paris, Nice, Lyon) en DB."""
        from models.tertiaire import TertiaireEfa

        names = [
            "EFA Siege HELIOS Paris",
            "EFA Hotel HELIOS Nice",
            "EFA Bureau Regional Lyon",
        ]
        for name in names:
            efa = seeded_db.query(TertiaireEfa).filter_by(nom=name).first()
            assert efa is not None, f"EFA '{name}' non trouvee"

    def test_efa_paris_mono(self, seeded_db):
        """EFA Paris : 1 batiment, 1 responsabilite, statut ACTIVE."""
        from models.tertiaire import TertiaireEfa, TertiaireEfaBuilding, TertiaireResponsibility
        from models.enums import EfaStatut

        efa = seeded_db.query(TertiaireEfa).filter_by(nom="EFA Siege HELIOS Paris").first()
        assert efa.statut == EfaStatut.ACTIVE
        buildings = seeded_db.query(TertiaireEfaBuilding).filter_by(efa_id=efa.id).all()
        assert len(buildings) >= 1
        resps = seeded_db.query(TertiaireResponsibility).filter_by(efa_id=efa.id).all()
        assert len(resps) >= 1

    def test_efa_nice_multi(self, seeded_db):
        """EFA Nice : 2 batiments, 2 responsabilites, statut ACTIVE."""
        from models.tertiaire import TertiaireEfa, TertiaireEfaBuilding, TertiaireResponsibility

        efa = seeded_db.query(TertiaireEfa).filter_by(nom="EFA Hotel HELIOS Nice").first()
        assert efa is not None
        buildings = seeded_db.query(TertiaireEfaBuilding).filter_by(efa_id=efa.id).all()
        assert len(buildings) >= 2
        resps = seeded_db.query(TertiaireResponsibility).filter_by(efa_id=efa.id).all()
        assert len(resps) >= 2

    def test_efa_nice_multioccupation(self, seeded_db):
        """EFA Nice : 2 roles differents (proprietaire + locataire)."""
        from models.tertiaire import TertiaireEfa, TertiaireResponsibility

        efa = seeded_db.query(TertiaireEfa).filter_by(nom="EFA Hotel HELIOS Nice").first()
        resps = seeded_db.query(TertiaireResponsibility).filter_by(efa_id=efa.id).all()
        roles = set(r.role.value if hasattr(r.role, "value") else str(r.role) for r in resps)
        assert len(roles) >= 2, f"Expected 2+ roles, got {roles}"

    def test_efa_nice_has_event(self, seeded_db):
        """EFA Nice : au moins 1 PerimeterEvent."""
        from models.tertiaire import TertiaireEfa, TertiairePerimeterEvent

        efa = seeded_db.query(TertiaireEfa).filter_by(nom="EFA Hotel HELIOS Nice").first()
        events = seeded_db.query(TertiairePerimeterEvent).filter_by(efa_id=efa.id).all()
        assert len(events) >= 1

    def test_efa_lyon_conforme(self, seeded_db):
        """EFA Lyon : statut ACTIVE, declaration submitted."""
        from models.tertiaire import TertiaireEfa, TertiaireDeclaration
        from models.enums import EfaStatut, DeclarationStatus

        efa = seeded_db.query(TertiaireEfa).filter_by(nom="EFA Bureau Regional Lyon").first()
        assert efa.statut == EfaStatut.ACTIVE
        decl = seeded_db.query(TertiaireDeclaration).filter_by(efa_id=efa.id, year=2024).first()
        assert decl is not None
        assert decl.status == DeclarationStatus.SUBMITTED_SIMULATED

    def test_declarations_exist(self, seeded_db):
        """Chaque EFA a 1 declaration annee 2024."""
        from models.tertiaire import TertiaireEfa, TertiaireDeclaration

        names = [
            "EFA Siege HELIOS Paris",
            "EFA Hotel HELIOS Nice",
            "EFA Bureau Regional Lyon",
        ]
        for name in names:
            efa = seeded_db.query(TertiaireEfa).filter_by(nom=name).first()
            decl = seeded_db.query(TertiaireDeclaration).filter_by(efa_id=efa.id, year=2024).first()
            assert decl is not None, f"Declaration 2024 manquante pour {name}"

    def test_checklist_structure(self, seeded_db):
        """checklist_json contient les 4 champs attendus."""
        import json
        from models.tertiaire import TertiaireEfa, TertiaireDeclaration

        efa = seeded_db.query(TertiaireEfa).filter_by(nom="EFA Siege HELIOS Paris").first()
        decl = seeded_db.query(TertiaireDeclaration).filter_by(efa_id=efa.id, year=2024).first()
        raw = decl.checklist_json
        assert raw is not None
        cl = json.loads(raw) if isinstance(raw, str) else raw
        for key in ["surface_renseignee", "consommations_importees", "attestation_affichage", "referent_designe"]:
            assert key in cl, f"Cle manquante dans checklist: {key}"

    def test_buildings_linked(self, seeded_db):
        """Chaque EfaBuilding a un building_id valide."""
        from models.tertiaire import TertiaireEfa, TertiaireEfaBuilding

        efa = seeded_db.query(TertiaireEfa).filter_by(nom="EFA Siege HELIOS Paris").first()
        buildings = seeded_db.query(TertiaireEfaBuilding).filter_by(efa_id=efa.id).all()
        for b in buildings:
            assert b.building_id is not None
            bat = seeded_db.query(Batiment).filter_by(id=b.building_id).first()
            assert bat is not None, f"Batiment {b.building_id} non trouve"

    def test_seed_idempotent(self, seeded_db):
        """Seed 2 fois → pas de doublon EFA."""
        from models.tertiaire import TertiaireEfa
        from services.demo_seed.gen_tertiaire_efa import seed_tertiaire_efa

        names_list = [
            "EFA Siege HELIOS Paris",
            "EFA Hotel HELIOS Nice",
            "EFA Bureau Regional Lyon",
        ]

        # Build helios_sites dict
        sites = seeded_db.query(Site).filter(Site.actif == True).all()
        helios_sites = {}
        for s in sites:
            name_lower = s.nom.lower()
            if "paris" in name_lower:
                helios_sites["paris"] = s
            elif "nice" in name_lower:
                helios_sites["nice"] = s
            elif "lyon" in name_lower:
                helios_sites["lyon"] = s

        count_before = seeded_db.query(TertiaireEfa).filter(
            TertiaireEfa.nom.in_(names_list)
        ).count()

        # Re-seed
        seed_tertiaire_efa(seeded_db, helios_sites)

        count_after = seeded_db.query(TertiaireEfa).filter(
            TertiaireEfa.nom.in_(names_list)
        ).count()

        assert count_after == count_before, "Seed non idempotent : doublons crees"
