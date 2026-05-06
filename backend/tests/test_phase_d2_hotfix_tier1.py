"""
PROMEOS — Tests cardinaux Phase D-2 hotfix Tier 1 (3 P0 audit deep multi-agents Phase D).

Couvre :
- P0.1 TURPE 7 dates (1/02/2025 mouvement exceptionnel CRE, pas 1/08/2025 calendrier annuel)
- P0.2 Codes FTA canoniques CRE (BTINFCU4 + BTINFMU4 + BTSUPCU + BTSUPLU + HTACU5 + HTALU5)
- P0.3 D6 Compteur ↔ Meter bridge (ADR-D-01 Option C)

Sources :
- docs/audits/AUDIT_TURPE7_DATES_2026_05_07.md
- docs/audits/AUDIT_CODES_FTA_TURPE7_2026_05_07.md
- docs/audits/AUDIT_D6_DUALITE_RUNTIME_2026_05_07.md
"""

from __future__ import annotations

import yaml
from pathlib import Path

import pytest


# ─── P0.1 — TURPE 7 dates application ───────────────────────────────────────


def test_phase_d2_turpe_7_date_application_canonique():
    """P0.1 cardinal : TURPE 7 valid_from = 2025-02-01 (mouvement exceptionnel CRE)."""
    yaml_path = Path(__file__).resolve().parent.parent / "config" / "tarifs_reglementaires.yaml"
    with yaml_path.open(encoding="utf-8") as f:
        config = yaml.safe_load(f)

    turpe = config.get("turpe", {})
    assert turpe.get("valid_from") == "2025-02-01", (
        f"P0.1 BLOQUANT : TURPE 7 valid_from={turpe.get('valid_from')!r} "
        f"attendu '2025-02-01' (mouvement exceptionnel CRE délibération 2025-78)"
    )
    assert turpe.get("version") == 7


def test_phase_d2_turpe_6_valid_to_aligned():
    """P0.1 : TURPE 6 valid_to = 2025-01-31 (cohérent avec TURPE 7 du 2025-02-01)."""
    yaml_path = Path(__file__).resolve().parent.parent / "config" / "tarifs_reglementaires.yaml"
    with yaml_path.open(encoding="utf-8") as f:
        config = yaml.safe_load(f)

    turpe_6 = config.get("turpe_6", {})
    assert turpe_6.get("valid_to") == "2025-01-31", (
        f"P0.1 BLOQUANT : TURPE 6 valid_to={turpe_6.get('valid_to')!r} "
        f"attendu '2025-01-31' (transition close par TURPE 7 du 1/02/2025)"
    )


def test_phase_d2_turpe_dates_constants_doctrine():
    """P0.1 : constantes doctrine `TURPE_7_DATE_APPLICATION` + `TURPE_6_DATE_FIN` exposées."""
    from doctrine.constants import TURPE_6_DATE_FIN, TURPE_7_DATE_APPLICATION

    assert TURPE_7_DATE_APPLICATION == "2025-02-01"
    assert TURPE_6_DATE_FIN == "2025-01-31"


def test_phase_d2_turpe_chronologie_coherente():
    """P0.1 : chronologie TURPE 6 valid_to < TURPE 7 valid_from (pas d'overlap)."""
    yaml_path = Path(__file__).resolve().parent.parent / "config" / "tarifs_reglementaires.yaml"
    with yaml_path.open(encoding="utf-8") as f:
        config = yaml.safe_load(f)

    turpe_6_valid_to = config.get("turpe_6", {}).get("valid_to")
    turpe_7_valid_from = config.get("turpe", {}).get("valid_from")
    assert turpe_6_valid_to < turpe_7_valid_from, (
        f"P0.1 BLOQUANT : chronologie cassée TURPE 6 ({turpe_6_valid_to}) vs TURPE 7 ({turpe_7_valid_from})"
    )


# ─── P0.2 — Codes FTA canoniques CRE ────────────────────────────────────────


def test_phase_d2_canonical_fta_codes_exposed():
    """P0.2 : `CANONICAL_FTA_CODES_TURPE_7` exposé dans doctrine."""
    from doctrine.constants import CANONICAL_FTA_CODES_TURPE_7

    expected_canonical = {"BTINFCU4", "BTINFMU4", "BTSUPCU", "BTSUPLU", "HTACU5", "HTALU5"}
    assert set(CANONICAL_FTA_CODES_TURPE_7) == expected_canonical, (
        f"P0.2 BLOQUANT : codes FTA canoniques attendus {expected_canonical}, reçu {set(CANONICAL_FTA_CODES_TURPE_7)}"
    )


def test_phase_d2_canonical_fta_codes_pass_validator():
    """P0.2 : tous les codes canoniques passent le validator C64 Phase D-1bis."""
    from doctrine.constants import CANONICAL_FTA_CODES_TURPE_7
    from models.patrimoine import DeliveryPoint

    for canonical_code in CANONICAL_FTA_CODES_TURPE_7:
        dp = DeliveryPoint(code=f"77999000000{hash(canonical_code) % 1000:03d}", site_id=1)
        # Doit passer sans ValueError (code canonique CRE)
        dp.code_fta = canonical_code
        assert dp.code_fta == canonical_code, f"P0.2 : code canonique {canonical_code} rejeté"


def test_phase_d2_legacy_invented_codes_no_longer_in_models():
    """P0.2 : codes inventés Phase D-1 (BT_HCH_PRO, etc.) absents des commentaires modèle."""
    from pathlib import Path

    patrimoine_path = Path(__file__).resolve().parent.parent / "models" / "patrimoine.py"
    src = patrimoine_path.read_text(encoding="utf-8")

    legacy_invented = ["BT_HCH_PRO", "BT_BASE_PRO", "BT_PRO_LU", "HTA_LU_BASE_4P"]
    for code in legacy_invented:
        # Tolérer mention du code dans un commentaire qui le qualifie d'invalide ?
        # Pour le hotfix, exigence stricte = aucune mention résiduelle.
        if code in src:
            occurrences = [line for line in src.split("\n") if code in line]
            pytest.fail(
                f"P0.2 BLOQUANT : code inventé {code!r} encore présent dans patrimoine.py — "
                f"{len(occurrences)} occurrence(s) :\n" + "\n".join(f"  {ln}" for ln in occurrences)
            )


def test_phase_d2_invented_legacy_codes_rejected_by_validator():
    """P1-4 fix code-reviewer : validator strict rejette les codes inventés Phase D-1.

    Pattern Pilier 9 ADR-016 : Phase D-1bis regex permissive → Phase D-2.2 Enum strict.
    """
    from models.patrimoine import DeliveryPoint

    invented_codes = ["BT_HCH_PRO", "BT_BASE_PRO", "BT_PRO_LU", "HTA_LU_BASE_4P"]
    for invented in invented_codes:
        dp = DeliveryPoint(code=f"77999099900{abs(hash(invented)) % 1000:03d}", site_id=1)
        with pytest.raises(ValueError, match="C64.*Phase D-2.2"):
            dp.code_fta = invented


def test_phase_d2_fta_code_enum_canonique_aligned():
    """P0.2 / P1-4 : Enum FtaCode aligné avec CANONICAL_FTA_CODES_TURPE_7."""
    from doctrine.constants import CANONICAL_FTA_CODES_TURPE_7
    from models.enums import FtaCode

    enum_values = {fc.value for fc in FtaCode}
    canonical_set = set(CANONICAL_FTA_CODES_TURPE_7)
    assert enum_values == canonical_set, (
        f"Mismatch FtaCode Enum {enum_values} vs CANONICAL_FTA_CODES_TURPE_7 {canonical_set}"
    )


def test_phase_d2_canonical_fta_compteur_persist(app_client):
    """P0.2 : DeliveryPoint persisté avec `BTINFCU4` canonique (test d'intégration)."""
    from models import EntiteJuridique, Organisation, Portefeuille, Site, TypeSite
    from models.enums import DeliveryPointEnergyType
    from models.patrimoine import DeliveryPoint

    _, SessionLocal = app_client
    db = SessionLocal()
    try:
        org = Organisation(nom="OrgD2P02", siren="999500001")
        db.add(org)
        db.flush()
        ej = EntiteJuridique(nom="EJD2P02", siren="999500001", organisation_id=org.id)
        db.add(ej)
        db.flush()
        pf = Portefeuille(nom="PFD2P02", entite_juridique_id=ej.id)
        db.add(pf)
        db.flush()
        site = Site(nom="SD2P02", type=TypeSite.BUREAU, actif=True, portefeuille_id=pf.id)
        db.add(site)
        db.flush()

        dp = DeliveryPoint(
            code="14999500000001",
            energy_type=DeliveryPointEnergyType.ELEC,
            site_id=site.id,
            categorie_turpe="C5",
            domaine_tension="BT≤36kVA",
            code_fta="BTINFCU4",  # canonique CRE
            version_turpe="TURPE_7",
        )
        db.add(dp)
        db.commit()
        db.refresh(dp)
        assert dp.code_fta == "BTINFCU4"
    finally:
        db.close()


# ─── P0.3 — D6 Compteur/Meter bridge ────────────────────────────────────────


def test_phase_d2_bridge_module_exists():
    """P0.3 : module `services/compteur_meter_bridge.py` créé."""
    from services import compteur_meter_bridge

    assert hasattr(compteur_meter_bridge, "ensure_meter_pair")
    assert hasattr(compteur_meter_bridge, "find_meter_by_compteur")


def test_phase_d2_bridge_creates_meter_for_orphan_compteur(app_client):
    """P0.3 : `ensure_meter_pair` crée un Meter sœur si absent (cas wizard onboarding)."""
    from models import EntiteJuridique, Organisation, Portefeuille, Site, TypeSite
    from models.compteur import Compteur
    from models.enums import TypeCompteur
    from models.energy_models import Meter
    from services.compteur_meter_bridge import ensure_meter_pair

    _, SessionLocal = app_client
    db = SessionLocal()
    try:
        org = Organisation(nom="OrgD2P03", siren="999500002")
        db.add(org)
        db.flush()
        ej = EntiteJuridique(nom="EJD2P03", siren="999500002", organisation_id=org.id)
        db.add(ej)
        db.flush()
        pf = Portefeuille(nom="PFD2P03", entite_juridique_id=ej.id)
        db.add(pf)
        db.flush()
        site = Site(nom="SD2P03", type=TypeSite.BUREAU, actif=True, portefeuille_id=pf.id)
        db.add(site)
        db.flush()

        # Créer Compteur sans Meter sœur
        compteur = Compteur(
            site_id=site.id,
            type=TypeCompteur.ELECTRICITE,
            numero_serie="D2-BRIDGE-001",
            meter_id="14999500000999",
            actif=True,
        )
        db.add(compteur)
        db.flush()

        # Bridge cardinal
        meter = ensure_meter_pair(db, compteur)
        assert meter is not None
        assert meter.numero_serie == "D2-BRIDGE-001"
        assert meter.site_id == site.id

        # Vérifier que ré-appeler retourne le même Meter (idempotent)
        meter2 = ensure_meter_pair(db, compteur)
        assert meter2.id == meter.id
    finally:
        db.close()


def test_phase_d2_bridge_anti_cycle_self_reference(app_client):
    """P1-1 fix code-reviewer : `ensure_meter_pair` détecte cycle auto-référence."""
    from models import EntiteJuridique, Organisation, Portefeuille, Site, TypeSite
    from models.compteur import Compteur
    from models.enums import TypeCompteur
    from services.compteur_meter_bridge import ensure_meter_pair

    _, SessionLocal = app_client
    db = SessionLocal()
    try:
        org = Organisation(nom="OrgD2Cycle", siren="999500004")
        db.add(org)
        db.flush()
        ej = EntiteJuridique(nom="EJD2Cycle", siren="999500004", organisation_id=org.id)
        db.add(ej)
        db.flush()
        pf = Portefeuille(nom="PFD2Cycle", entite_juridique_id=ej.id)
        db.add(pf)
        db.flush()
        site = Site(nom="SD2Cycle", type=TypeSite.BUREAU, actif=True, portefeuille_id=pf.id)
        db.add(site)
        db.flush()

        # Compteur auto-référencé (pathological — devrait être empêché en DB mais pas par contrainte FK)
        c = Compteur(
            site_id=site.id,
            type=TypeCompteur.ELECTRICITE,
            numero_serie="D2-CYCLE-001",
            actif=True,
        )
        db.add(c)
        db.flush()
        # Phase D-3 Tier 2 DOC-2 ajoute validator @validates au niveau model qui
        # intercepte l'auto-référence AVANT le bridge. Le validator lève "auto-référence
        # cardinal interdite — anti-cycle D6 self-FK". Defense in depth :
        # le bridge `ensure_meter_pair` reste capable de détecter cycles plus profonds (A→B→A).
        with pytest.raises(ValueError, match="anti-cycle D6"):
            c.sub_meter_of_id = c.id
        # Si on bypass le validator (set direct via __dict__), le bridge intercepte aussi :
        c.__dict__["sub_meter_of_id"] = c.id
        with pytest.raises(ValueError, match="cycle détecté"):
            ensure_meter_pair(db, c)
    finally:
        db.rollback()
        db.close()


def test_phase_d2_bridge_org_scoping_site_id(app_client):
    """P1-3 fix code-reviewer : `find_meter_by_compteur` scope par site_id (anti cross-tenant)."""
    from models import EntiteJuridique, Organisation, Portefeuille, Site, TypeSite
    from models.compteur import Compteur
    from models.energy_models import EnergyVector, Meter
    from models.enums import TypeCompteur
    from services.compteur_meter_bridge import find_meter_by_compteur

    _, SessionLocal = app_client
    db = SessionLocal()
    try:
        org = Organisation(nom="OrgD2Scope", siren="999500005")
        db.add(org)
        db.flush()
        ej = EntiteJuridique(nom="EJD2Scope", siren="999500005", organisation_id=org.id)
        db.add(ej)
        db.flush()
        pf = Portefeuille(nom="PFD2Scope", entite_juridique_id=ej.id)
        db.add(pf)
        db.flush()
        # 2 sites distincts (simulent 2 tenants)
        site_a = Site(nom="SiteA", type=TypeSite.BUREAU, actif=True, portefeuille_id=pf.id)
        site_b = Site(nom="SiteB", type=TypeSite.BUREAU, actif=True, portefeuille_id=pf.id)
        db.add_all([site_a, site_b])
        db.flush()

        # Meter sur Site A avec un meter_id donné
        meter_a = Meter(
            meter_id="14999000099001",
            name="MeterSiteA",
            energy_vector=EnergyVector.ELECTRICITY,
            site_id=site_a.id,
            is_active=True,
        )
        db.add(meter_a)
        db.flush()

        # Compteur sur Site B avec MÊME meter_id (collision cross-tenant théorique)
        compteur_b = Compteur(
            site_id=site_b.id,
            type=TypeCompteur.ELECTRICITE,
            meter_id="14999000099001",  # collision !
            actif=True,
        )
        db.add(compteur_b)
        db.flush()

        # find_meter_by_compteur sur Site B ne doit PAS retourner Meter Site A
        found = find_meter_by_compteur(db, compteur_b)
        assert found is None, (
            "P1-3 BLOQUANT : find_meter_by_compteur n'est pas scope par site_id → risque cross-tenant cardinal"
        )
    finally:
        db.close()


def test_phase_d2_bridge_propagates_hierarchy(app_client):
    """P0.3 : bridge propage `Compteur.sub_meter_of_id` → `Meter.parent_meter_id`."""
    from models import EntiteJuridique, Organisation, Portefeuille, Site, TypeSite
    from models.compteur import Compteur
    from models.enums import TypeCompteur
    from services.compteur_meter_bridge import ensure_meter_pair

    _, SessionLocal = app_client
    db = SessionLocal()
    try:
        org = Organisation(nom="OrgD2P03H", siren="999500003")
        db.add(org)
        db.flush()
        ej = EntiteJuridique(nom="EJD2P03H", siren="999500003", organisation_id=org.id)
        db.add(ej)
        db.flush()
        pf = Portefeuille(nom="PFD2P03H", entite_juridique_id=ej.id)
        db.add(pf)
        db.flush()
        site = Site(nom="SD2P03H", type=TypeSite.BUREAU, actif=True, portefeuille_id=pf.id)
        db.add(site)
        db.flush()

        # Compteur principal
        parent_compteur = Compteur(
            site_id=site.id,
            type=TypeCompteur.ELECTRICITE,
            numero_serie="D2-PARENT-001",
            actif=True,
        )
        db.add(parent_compteur)
        db.flush()

        # Sub-compteur CVC rattaché
        sub_compteur = Compteur(
            site_id=site.id,
            type=TypeCompteur.ELECTRICITE,
            numero_serie="D2-SUB-CVC-001",
            actif=True,
            sub_meter_of_id=parent_compteur.id,
            sub_meter_usage="CVC",
        )
        db.add(sub_compteur)
        db.flush()

        # Bridge sub_compteur → propage hiérarchie
        sub_meter = ensure_meter_pair(db, sub_compteur)
        assert sub_meter.parent_meter_id is not None, (
            "P0.3 BLOQUANT : Meter sub n'a pas hérité parent_meter_id du Compteur parent"
        )
    finally:
        db.close()


def test_phase_d2_compteur_docstring_pointe_meter():
    """P0.3 : docstring `Compteur.sub_meter_of_id` mentionne `Meter.parent_meter_id` runtime."""
    from pathlib import Path

    compteur_path = Path(__file__).resolve().parent.parent / "models" / "compteur.py"
    src = compteur_path.read_text(encoding="utf-8")

    assert "Meter.parent_meter_id" in src, (
        "P0.3 : docstring Compteur doit pointer vers Meter.parent_meter_id (SoT runtime)"
    )
    assert "ADR-D-01" in src or "compteur_meter_bridge" in src, (
        "P0.3 : docstring doit référencer ADR-D-01 ou le module bridge"
    )


# ─── ADR + audits cardinaux livrés ──────────────────────────────────────────


def test_phase_d2_audit_docs_livres():
    """Phase D-2 : 3 docs audits cardinaux livrés."""
    from pathlib import Path

    repo_root = Path(__file__).resolve().parent.parent.parent
    audits = repo_root / "docs" / "audits"
    expected = [
        "AUDIT_TURPE7_DATES_2026_05_07.md",
        "AUDIT_CODES_FTA_TURPE7_2026_05_07.md",
        "AUDIT_D6_DUALITE_RUNTIME_2026_05_07.md",
    ]
    missing = [d for d in expected if not (audits / d).exists()]
    assert not missing, f"Phase D-2 BLOQUANT : audits manquants {missing}"


def test_phase_d2_adr_d01_livre():
    """Phase D-2 : ADR-D-01 dualité Meter/Compteur livré."""
    from pathlib import Path

    repo_root = Path(__file__).resolve().parent.parent.parent
    adr = repo_root / "docs" / "adr" / "ADR-D-01-meter-compteur-duality.md"
    assert adr.exists(), "Phase D-2 BLOQUANT : ADR-D-01 absent"

    src = adr.read_text(encoding="utf-8")
    assert "Option C" in src, "ADR-D-01 doit documenter Option C retenue"
    assert "ensure_meter_pair" in src, "ADR-D-01 doit référencer le bridge"
