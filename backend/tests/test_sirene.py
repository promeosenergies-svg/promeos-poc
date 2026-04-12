"""
PROMEOS - Tests Sirene (mapping, import, recherche, onboarding, anti-doublons).

Couvre :
- Mapping CSV → modele (UL, ETAB, doublons)
- Import full upsert idempotent
- Import delta incremental
- Recherche API (nom, SIREN, SIRET)
- Onboarding from-sirene (creation, anti-doublons, garde-fous)
- Cas metier : mono-etab, multi-sites, ferme, doublon SIREN/SIRET
"""

import csv
import io
import json
import os
import tempfile
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models.base import Base
from models.sirene import (
    SireneUniteLegale,
    SireneEtablissement,
    SireneDoublon,
    SireneSyncRun,
    CustomerCreationTrace,
)
from models import (
    Organisation,
    EntiteJuridique,
    Portefeuille,
    Site,
    Batiment,
    Compteur,
)
from services.sirene_import import (
    _map_row,
    UL_COLUMN_MAP,
    ETAB_COLUMN_MAP,
    DOUBLONS_COLUMN_MAP,
    import_full_unites_legales,
    import_full_etablissements,
    import_doublons,
    import_delta_unites_legales,
    run_sirene_import,
)


# ══════════════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════════════


@pytest.fixture
def db():
    """In-memory SQLite DB with all PROMEOS tables."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_ul_csv(tmp_path):
    """Create a minimal stockUniteLegale CSV."""
    rows = [
        {
            "siren": "552032534",
            "statutDiffusionUniteLegale": "O",
            "dateCreationUniteLegale": "1959-07-30",
            "sigleUniteLegale": "",
            "denominationUniteLegale": "CARREFOUR",
            "nomUniteLegale": "",
            "categorieJuridiqueUniteLegale": "5710",
            "activitePrincipaleUniteLegale": "47.11F",
            "nomenclatureActivitePrincipaleUniteLegale": "NAFRev2",
            "nicSiegeUniteLegale": "00017",
            "etatAdministratifUniteLegale": "A",
            "caractereEmployeurUniteLegale": "O",
            "trancheEffectifsUniteLegale": "53",
            "anneeEffectifsUniteLegale": "2023",
            "dateDernierTraitementUniteLegale": "2025-12-15T10:00:00",
            "categorieEntreprise": "GE",
            "economieSocialeSolidaireUniteLegale": "N",
            "societeMissionUniteLegale": "N",
            "activitePrincipaleNAF25UniteLegale": "47.11",
        },
        {
            "siren": "444786511",
            "statutDiffusionUniteLegale": "O",
            "dateCreationUniteLegale": "2002-05-06",
            "sigleUniteLegale": "EDF",
            "denominationUniteLegale": "ELECTRICITE DE FRANCE",
            "nomUniteLegale": "",
            "categorieJuridiqueUniteLegale": "5710",
            "activitePrincipaleUniteLegale": "35.11Z",
            "nomenclatureActivitePrincipaleUniteLegale": "NAFRev2",
            "nicSiegeUniteLegale": "00019",
            "etatAdministratifUniteLegale": "A",
            "caractereEmployeurUniteLegale": "O",
            "trancheEffectifsUniteLegale": "53",
            "anneeEffectifsUniteLegale": "2023",
            "dateDernierTraitementUniteLegale": "2025-11-20T08:30:00",
            "categorieEntreprise": "GE",
            "economieSocialeSolidaireUniteLegale": "N",
            "societeMissionUniteLegale": "N",
            "activitePrincipaleNAF25UniteLegale": "35.11",
        },
    ]
    path = tmp_path / "stockUniteLegale.csv"
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return str(path)


@pytest.fixture
def sample_etab_csv(tmp_path):
    """Create a minimal stockEtablissement CSV."""
    rows = [
        {
            "siren": "552032534",
            "nic": "00017",
            "siret": "55203253400017",
            "statutDiffusionEtablissement": "O",
            "dateCreationEtablissement": "1996-01-01",
            "trancheEffectifsEtablissement": "53",
            "anneeEffectifsEtablissement": "2023",
            "dateDernierTraitementEtablissement": "2025-12-15T10:00:00",
            "etablissementSiege": "true",
            "complementAdresseEtablissement": "",
            "numeroVoieEtablissement": "93",
            "typeVoieEtablissement": "AV",
            "libelleVoieEtablissement": "DE PARIS",
            "codePostalEtablissement": "91300",
            "libelleCommuneEtablissement": "MASSY",
            "codeCommuneEtablissement": "91377",
            "etatAdministratifEtablissement": "A",
            "enseigne1Etablissement": "CARREFOUR SIEGE",
            "denominationUsuelleEtablissement": "",
            "activitePrincipaleEtablissement": "47.11F",
            "nomenclatureActivitePrincipaleEtablissement": "NAFRev2",
            "caractereEmployeurEtablissement": "O",
            "activitePrincipaleNAF25Etablissement": "47.11",
        },
        {
            "siren": "552032534",
            "nic": "01234",
            "siret": "55203253401234",
            "statutDiffusionEtablissement": "O",
            "dateCreationEtablissement": "2005-03-15",
            "trancheEffectifsEtablissement": "21",
            "anneeEffectifsEtablissement": "2023",
            "dateDernierTraitementEtablissement": "2025-10-01T09:00:00",
            "etablissementSiege": "false",
            "complementAdresseEtablissement": "",
            "numeroVoieEtablissement": "1",
            "typeVoieEtablissement": "RUE",
            "libelleVoieEtablissement": "DU COMMERCE",
            "codePostalEtablissement": "75015",
            "libelleCommuneEtablissement": "PARIS",
            "codeCommuneEtablissement": "75115",
            "etatAdministratifEtablissement": "A",
            "enseigne1Etablissement": "CARREFOUR PARIS 15",
            "denominationUsuelleEtablissement": "",
            "activitePrincipaleEtablissement": "47.11F",
            "nomenclatureActivitePrincipaleEtablissement": "NAFRev2",
            "caractereEmployeurEtablissement": "O",
            "activitePrincipaleNAF25Etablissement": "47.11",
        },
        {
            "siren": "552032534",
            "nic": "05678",
            "siret": "55203253405678",
            "statutDiffusionEtablissement": "O",
            "dateCreationEtablissement": "2010-06-01",
            "trancheEffectifsEtablissement": "0",
            "anneeEffectifsEtablissement": "2023",
            "dateDernierTraitementEtablissement": "2024-01-15T10:00:00",
            "etablissementSiege": "false",
            "complementAdresseEtablissement": "",
            "numeroVoieEtablissement": "5",
            "typeVoieEtablissement": "BD",
            "libelleVoieEtablissement": "GAMBETTA",
            "codePostalEtablissement": "69003",
            "libelleCommuneEtablissement": "LYON",
            "codeCommuneEtablissement": "69383",
            "etatAdministratifEtablissement": "F",
            "enseigne1Etablissement": "CARREFOUR LYON (FERME)",
            "denominationUsuelleEtablissement": "",
            "activitePrincipaleEtablissement": "47.11F",
            "nomenclatureActivitePrincipaleEtablissement": "NAFRev2",
            "caractereEmployeurEtablissement": "",
            "activitePrincipaleNAF25Etablissement": "47.11",
        },
    ]
    path = tmp_path / "stockEtablissement.csv"
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return str(path)


@pytest.fixture
def sample_doublons_csv(tmp_path):
    """Create a minimal stockDoublons CSV."""
    rows = [
        {"siren": "552032534", "sirenDoublon": "999888777", "dateDernierTraitementDoublon": "2025-06-01"},
    ]
    path = tmp_path / "stockDoublons.csv"
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return str(path)


SNAPSHOT = datetime(2026, 3, 31, tzinfo=timezone.utc)


# ══════════════════════════════════════════════════════════════════════
# Tests Mapping
# ══════════════════════════════════════════════════════════════════════


class TestMapping:
    def test_map_row_ul(self):
        row = {
            "siren": "552032534",
            "denominationUniteLegale": "CARREFOUR",
            "etatAdministratifUniteLegale": "A",
            "activitePrincipaleUniteLegale": "47.11F",
            "dateDernierTraitementUniteLegale": "2025-12-15T10:00:00",
        }
        mapped = _map_row(row, UL_COLUMN_MAP)
        assert mapped["siren"] == "552032534"
        assert mapped["denomination"] == "CARREFOUR"
        assert mapped["etat_administratif"] == "A"
        assert mapped["activite_principale"] == "47.11F"

    def test_map_row_etab(self):
        row = {
            "siret": "55203253400017",
            "siren": "552032534",
            "nic": "00017",
            "enseigne1Etablissement": "CARREFOUR SIEGE",
            "codePostalEtablissement": "91300",
            "libelleCommuneEtablissement": "MASSY",
            "etatAdministratifEtablissement": "A",
            "etablissementSiege": "true",
        }
        mapped = _map_row(row, ETAB_COLUMN_MAP)
        assert mapped["siret"] == "55203253400017"
        assert mapped["siren"] == "552032534"
        assert mapped["enseigne"] == "CARREFOUR SIEGE"
        assert mapped["etablissement_siege"] is True
        assert mapped["code_postal"] == "91300"

    def test_map_row_doublons(self):
        row = {"siren": "552032534", "sirenDoublon": "999888777", "dateDernierTraitementDoublon": "2025-06-01"}
        mapped = _map_row(row, DOUBLONS_COLUMN_MAP)
        assert mapped["siren"] == "552032534"
        assert mapped["siren_doublon"] == "999888777"

    def test_map_row_empty_values(self):
        row = {"siren": "123456789", "denominationUniteLegale": "  ", "etatAdministratifUniteLegale": "A"}
        mapped = _map_row(row, UL_COLUMN_MAP)
        assert mapped["siren"] == "123456789"
        assert mapped["denomination"] is None  # trimmed empty → None

    def test_map_row_invalid_siren_ignored(self):
        """Lignes avec SIREN invalide ne sont pas bloquees par _map_row (c'est l'import qui rejette)."""
        row = {"siren": "ABC", "denominationUniteLegale": "TEST"}
        mapped = _map_row(row, UL_COLUMN_MAP)
        assert mapped["siren"] == "ABC"  # mapping ne valide pas, l'import le fait


# ══════════════════════════════════════════════════════════════════════
# Tests Import Full
# ══════════════════════════════════════════════════════════════════════


class TestImportFull:
    def test_import_ul_full(self, db, sample_ul_csv):
        run = SireneSyncRun(sync_type="full", started_at=datetime.now(timezone.utc), status="running")
        db.add(run)
        db.flush()

        stats = import_full_unites_legales(db, sample_ul_csv, SNAPSHOT, run)
        assert stats["read"] == 2
        assert stats["inserted"] == 2
        assert stats["rejected"] == 0

        # Verify data
        carrefour = db.query(SireneUniteLegale).filter_by(siren="552032534").first()
        assert carrefour.denomination == "CARREFOUR"
        assert carrefour.activite_principale == "47.11F"
        assert carrefour.etat_administratif == "A"
        assert carrefour.categorie_entreprise == "GE"

    def test_import_ul_idempotent(self, db, sample_ul_csv):
        """Double import = pas de doublon, juste des updates si date plus recente."""
        run = SireneSyncRun(sync_type="full", started_at=datetime.now(timezone.utc), status="running")
        db.add(run)
        db.flush()

        stats1 = import_full_unites_legales(db, sample_ul_csv, SNAPSHOT, run)
        assert stats1["inserted"] == 2

        # Second import → 0 inserts, 0 updates (same data)
        stats2 = import_full_unites_legales(db, sample_ul_csv, SNAPSHOT, run)
        assert stats2["inserted"] == 0
        assert stats2["updated"] == 0

        # Total in DB = 2
        assert db.query(SireneUniteLegale).count() == 2

    def test_import_etab_full(self, db, sample_etab_csv):
        run = SireneSyncRun(sync_type="full", started_at=datetime.now(timezone.utc), status="running")
        db.add(run)
        db.flush()

        stats = import_full_etablissements(db, sample_etab_csv, SNAPSHOT, run)
        assert stats["read"] == 3
        assert stats["inserted"] == 3

        # Verify siege flag
        siege = db.query(SireneEtablissement).filter_by(siret="55203253400017").first()
        assert siege.etablissement_siege is True
        assert siege.libelle_commune == "MASSY"

        # Verify ferme
        ferme = db.query(SireneEtablissement).filter_by(siret="55203253405678").first()
        assert ferme.etat_administratif == "F"

    def test_import_doublons(self, db, sample_doublons_csv):
        run = SireneSyncRun(sync_type="doublons", started_at=datetime.now(timezone.utc), status="running")
        db.add(run)
        db.flush()

        stats = import_doublons(db, sample_doublons_csv, SNAPSHOT)
        assert stats["read"] == 1
        assert stats["inserted"] == 1

        d = db.query(SireneDoublon).first()
        assert d.siren == "552032534"
        assert d.siren_doublon == "999888777"


# ══════════════════════════════════════════════════════════════════════
# Tests Import Delta
# ══════════════════════════════════════════════════════════════════════


class TestImportDelta:
    def test_delta_skips_old_records(self, db, sample_ul_csv):
        run = SireneSyncRun(sync_type="delta", started_at=datetime.now(timezone.utc), status="running")
        db.add(run)
        db.flush()

        # Import delta with since AFTER all records → all skipped
        stats = import_delta_unites_legales(db, sample_ul_csv, SNAPSHOT, run, since="2026-01-01T00:00:00")
        assert stats["skipped"] == 2
        assert stats["inserted"] == 0

    def test_delta_imports_recent(self, db, sample_ul_csv):
        run = SireneSyncRun(sync_type="delta", started_at=datetime.now(timezone.utc), status="running")
        db.add(run)
        db.flush()

        # Import delta with since BEFORE all records → all imported
        stats = import_delta_unites_legales(db, sample_ul_csv, SNAPSHOT, run, since="2020-01-01")
        assert stats["inserted"] == 2
        assert stats["skipped"] == 0


# ══════════════════════════════════════════════════════════════════════
# Tests Orchestrateur
# ══════════════════════════════════════════════════════════════════════


class TestOrchestrator:
    def test_run_full_import(self, db, sample_ul_csv, sample_etab_csv):
        run = run_sirene_import(db, "full", ul_path=sample_ul_csv, etab_path=sample_etab_csv, snapshot_date=SNAPSHOT)
        assert run.status == "success"
        assert run.lines_read == 5  # 2 UL + 3 ETAB
        assert run.lines_inserted == 5
        assert run.correlation_id is not None

    def test_run_file_not_found(self, db):
        """Fichier inexistant → run status=failed, pas de crash."""
        run = run_sirene_import(db, "full", ul_path="/nonexistent.csv")
        assert run.status == "failed"
        assert "nonexistent" in run.error_message


# ══════════════════════════════════════════════════════════════════════
# Tests API + Onboarding (integration via TestClient)
# ══════════════════════════════════════════════════════════════════════


@pytest.fixture
def app_client(db):
    """FastAPI TestClient with isolated DB."""
    os.environ["DEMO_MODE"] = "true"

    from fastapi.testclient import TestClient
    from main import app
    from database import get_db

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client, db
    app.dependency_overrides.pop(get_db, None)


class TestSearchAPI:
    def test_search_empty_db(self, app_client):
        client, db = app_client
        resp = client.get("/api/reference/sirene/search", params={"q": "Carrefour"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0

    def test_search_by_name(self, app_client, sample_ul_csv):
        client, db = app_client
        run = SireneSyncRun(sync_type="full", started_at=datetime.now(timezone.utc), status="running")
        db.add(run)
        db.flush()
        import_full_unites_legales(db, sample_ul_csv, SNAPSHOT, run)

        resp = client.get("/api/reference/sirene/search", params={"q": "Carrefour"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["results"][0]["siren"] == "552032534"

    def test_search_by_siren(self, app_client, sample_ul_csv):
        client, db = app_client
        run = SireneSyncRun(sync_type="full", started_at=datetime.now(timezone.utc), status="running")
        db.add(run)
        db.flush()
        import_full_unites_legales(db, sample_ul_csv, SNAPSHOT, run)

        resp = client.get("/api/reference/sirene/search", params={"q": "552032534"})
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_get_unite_legale(self, app_client, sample_ul_csv):
        client, db = app_client
        run = SireneSyncRun(sync_type="full", started_at=datetime.now(timezone.utc), status="running")
        db.add(run)
        db.flush()
        import_full_unites_legales(db, sample_ul_csv, SNAPSHOT, run)

        resp = client.get("/api/reference/sirene/unites-legales/552032534")
        assert resp.status_code == 200
        assert resp.json()["denomination"] == "CARREFOUR"

    def test_get_unite_legale_not_found(self, app_client):
        client, db = app_client
        resp = client.get("/api/reference/sirene/unites-legales/000000000")
        assert resp.status_code == 404

    def test_get_etablissements(self, app_client, sample_etab_csv):
        client, db = app_client
        run = SireneSyncRun(sync_type="full", started_at=datetime.now(timezone.utc), status="running")
        db.add(run)
        db.flush()
        import_full_etablissements(db, sample_etab_csv, SNAPSHOT, run)

        resp = client.get("/api/reference/sirene/unites-legales/552032534/etablissements")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        # Siege first
        assert data["etablissements"][0]["etablissement_siege"] is True


class TestOnboardingFromSirene:
    def _seed_sirene(self, db, sample_ul_csv, sample_etab_csv):
        run = SireneSyncRun(sync_type="full", started_at=datetime.now(timezone.utc), status="running")
        db.add(run)
        db.flush()
        import_full_unites_legales(db, sample_ul_csv, SNAPSHOT, run)
        import_full_etablissements(db, sample_etab_csv, SNAPSHOT, run)

    def test_create_mono_etablissement(self, app_client, sample_ul_csv, sample_etab_csv):
        """Entreprise avec 1 seul etablissement selectionne."""
        client, db = app_client
        self._seed_sirene(db, sample_ul_csv, sample_etab_csv)

        resp = client.post(
            "/api/onboarding/from-sirene",
            json={
                "siren": "552032534",
                "etablissement_sirets": ["55203253400017"],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["organisation_id"] > 0
        assert data["entite_juridique_id"] > 0
        assert data["portefeuille_id"] > 0
        assert len(data["sites"]) == 1
        assert data["sites"][0]["siret"] == "55203253400017"

        # Verify NO batiment/compteur created
        assert db.query(Batiment).count() == 0
        assert db.query(Compteur).count() == 0

    def test_create_multi_sites(self, app_client, sample_ul_csv, sample_etab_csv):
        """Entreprise avec 2 etablissements selectionnes."""
        client, db = app_client
        self._seed_sirene(db, sample_ul_csv, sample_etab_csv)

        resp = client.post(
            "/api/onboarding/from-sirene",
            json={
                "siren": "552032534",
                "etablissement_sirets": ["55203253400017", "55203253401234"],
            },
        )
        assert resp.status_code == 200
        assert len(resp.json()["sites"]) == 2

    def test_blocage_siren_doublon(self, app_client, sample_ul_csv, sample_etab_csv):
        """SIREN deja existant → 409 CONFLICT."""
        client, db = app_client
        self._seed_sirene(db, sample_ul_csv, sample_etab_csv)

        # Premier appel → OK
        resp1 = client.post(
            "/api/onboarding/from-sirene",
            json={
                "siren": "552032534",
                "etablissement_sirets": ["55203253400017"],
            },
        )
        assert resp1.status_code == 200

        # Deuxieme appel → 409
        resp2 = client.post(
            "/api/onboarding/from-sirene",
            json={
                "siren": "552032534",
                "etablissement_sirets": ["55203253401234"],
            },
        )
        assert resp2.status_code == 409
        assert "SIREN_ALREADY_EXISTS" in str(resp2.json())

    def test_warning_siret_existant(self, app_client, sample_ul_csv, sample_etab_csv):
        """SIRET deja present sur un site → warning mais pas blocage."""
        client, db = app_client
        self._seed_sirene(db, sample_ul_csv, sample_etab_csv)

        # Pre-creer un site avec le SIRET du siege
        pf = Portefeuille(entite_juridique_id=None, nom="Test")
        # Need EJ first
        org = Organisation(nom="Test Org", siren="111111111", actif=True)
        db.add(org)
        db.flush()
        ej = EntiteJuridique(organisation_id=org.id, nom="Test EJ", siren="111111111")
        db.add(ej)
        db.flush()
        pf = Portefeuille(entite_juridique_id=ej.id, nom="Test PF")
        db.add(pf)
        db.flush()
        site = Site(portefeuille_id=pf.id, nom="Existing Site", type="BUREAU", siret="55203253400017", actif=True)
        db.add(site)
        db.commit()

        # Now create from sirene → should have warning
        resp = client.post(
            "/api/onboarding/from-sirene",
            json={
                "siren": "552032534",
                "etablissement_sirets": ["55203253400017"],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        siret_warnings = [w for w in data["warnings"] if w["type"] == "siret_exists"]
        assert len(siret_warnings) >= 1

    def test_siren_not_found_in_referentiel(self, app_client):
        """SIREN absent du referentiel → 404."""
        client, db = app_client
        resp = client.post(
            "/api/onboarding/from-sirene",
            json={
                "siren": "999999999",
                "etablissement_sirets": ["99999999900001"],
            },
        )
        assert resp.status_code == 404
        assert "SIREN_NOT_FOUND" in str(resp.json())

    def test_trace_created(self, app_client, sample_ul_csv, sample_etab_csv):
        """Verifie que la trace de creation est bien enregistree."""
        client, db = app_client
        self._seed_sirene(db, sample_ul_csv, sample_etab_csv)

        client.post(
            "/api/onboarding/from-sirene",
            json={
                "siren": "552032534",
                "etablissement_sirets": ["55203253400017"],
            },
        )

        trace = db.query(CustomerCreationTrace).first()
        assert trace is not None
        assert trace.source_siren == "552032534"
        assert trace.status == "success"
        assert trace.organisation_id is not None

    def test_no_batiment_no_compteur_no_obligation(self, app_client, sample_ul_csv, sample_etab_csv):
        """REGLE ABSOLUE : Sirene ne cree JAMAIS batiment, compteur, contrat, obligation."""
        client, db = app_client
        self._seed_sirene(db, sample_ul_csv, sample_etab_csv)

        client.post(
            "/api/onboarding/from-sirene",
            json={
                "siren": "552032534",
                "etablissement_sirets": ["55203253400017", "55203253401234"],
            },
        )

        # Verify: 0 batiment, 0 compteur
        from models import Obligation

        assert db.query(Batiment).count() == 0
        assert db.query(Compteur).count() == 0
        assert db.query(Obligation).count() == 0

    def test_etablissement_ferme_can_be_selected(self, app_client, sample_ul_csv, sample_etab_csv):
        """Un etablissement ferme peut etre selectionne (choix utilisateur)."""
        client, db = app_client
        self._seed_sirene(db, sample_ul_csv, sample_etab_csv)

        resp = client.post(
            "/api/onboarding/from-sirene",
            json={
                "siren": "552032534",
                "etablissement_sirets": ["55203253405678"],  # FERME
            },
        )
        assert resp.status_code == 200
        assert len(resp.json()["sites"]) == 1

    def test_siret_siren_mismatch(self, app_client, sample_ul_csv, sample_etab_csv):
        """SIRET n'appartenant pas au SIREN demande → 400."""
        client, db = app_client
        self._seed_sirene(db, sample_ul_csv, sample_etab_csv)

        # Seed un etablissement appartenant a un autre SIREN
        etab_other = SireneEtablissement(
            siret="99988877700011",
            siren="999888777",
            nic="00011",
            etat_administratif="A",
            statut_diffusion="O",
            snapshot_date=SNAPSHOT,
        )
        db.add(etab_other)
        db.commit()

        # Tenter de creer avec SIREN 552032534 mais SIRET d'un autre
        resp = client.post(
            "/api/onboarding/from-sirene",
            json={
                "siren": "552032534",
                "etablissement_sirets": ["99988877700011"],
            },
        )
        assert resp.status_code == 400
        assert "SIRET_SIREN_MISMATCH" in str(resp.json())

    def test_nom_unite_legale_in_response(self, app_client, sample_ul_csv):
        """Le schema renvoie nom_unite_legale pour les entreprises individuelles."""
        client, db = app_client
        # Seed une entreprise individuelle (denomination=None, nom_unite_legale=set)
        ul = SireneUniteLegale(
            siren="123456789",
            nom_unite_legale="DUPONT",
            prenom1="JEAN",
            etat_administratif="A",
            statut_diffusion="O",
            snapshot_date=SNAPSHOT,
        )
        db.add(ul)
        db.commit()

        resp = client.get("/api/reference/sirene/unites-legales/123456789")
        assert resp.status_code == 200
        data = resp.json()
        assert data["nom_unite_legale"] == "DUPONT"
        assert data["prenom1"] == "JEAN"


class TestSchemaValidation:
    def test_path_traversal_rejected(self):
        """Les chemins avec .. sont rejetes par le schema."""
        from schemas.sirene import SireneImportRequest

        with pytest.raises(Exception):
            SireneImportRequest(ul_path="../../etc/passwd")

    def test_absolute_path_rejected(self):
        from schemas.sirene import SireneImportRequest

        with pytest.raises(Exception):
            SireneImportRequest(ul_path="/etc/passwd")

    def test_relative_path_accepted(self):
        from schemas.sirene import SireneImportRequest

        req = SireneImportRequest(ul_path="stockUniteLegale.csv")
        assert req.ul_path == "stockUniteLegale.csv"

    def test_siret_max_50(self):
        """Plus de 50 SIRETs rejetes."""
        from schemas.sirene import OnboardingFromSireneRequest

        with pytest.raises(Exception):
            OnboardingFromSireneRequest(
                siren="552032534",
                etablissement_sirets=[f"5520325340{i:04d}" for i in range(51)],
            )

    def test_type_client_invalid(self):
        """Type client hors liste rejete."""
        from schemas.sirene import OnboardingFromSireneRequest

        with pytest.raises(Exception):
            OnboardingFromSireneRequest(
                siren="552032534",
                etablissement_sirets=["55203253400017"],
                type_client="invalide",
            )
