"""
PROMEOS — Tests cardinaux Phase 8.4 Sprint C-8 — 3 P0 audit Sprint C-8 fixés.

Couvre :
- D-Audit-C8-VNU-L336-Source-Field-001 P0 REG (tarifs YAML ligne 560 L.336-1 → L.336-2)
- D-Audit-C8-CGU-Archives-Accepted-002 P0 SEC (CNIL Article 7 — archive rejected runtime)
- D-Audit-C8-Helper-OPERAT-Orphan-003 P0 CR (helper ADR-020 wiré dans generate_operat_csv)
"""

from __future__ import annotations

from pathlib import Path


# ─── P0-001 — VNU L.336-2 cohérence cross-fichier ────────────────────────────


def test_phase84_vnu_l336_2_uniform_in_tarifs_yaml():
    """Phase 8.4 P0 REG cardinal : tarifs_reglementaires.yaml VNU section uniforme L.336-2."""
    yaml_path = Path(__file__).parent.parent / "config" / "tarifs_reglementaires.yaml"
    content = yaml_path.read_text(encoding="utf-8")

    # Section VNU (lignes 546+)
    vnu_section_idx = content.find("VNU (Versement pour Non-Usage")
    assert vnu_section_idx > 0, "Header VNU introuvable"
    next_section_idx = content.find("# ── Prix de référence", vnu_section_idx)
    vnu_section = content[vnu_section_idx:next_section_idx] if next_section_idx > 0 else content[vnu_section_idx:]

    # Toute mention L.336-x dans la section VNU doit être L.336-2 (Phase 8.4 fix)
    assert "L.336-2" in vnu_section or "L. 336-2" in vnu_section, (
        "Phase 8.4 BLOQUANT REG : article L.336-2 absent section VNU YAML"
    )
    # Anti-pattern : L.336-1 résiduel runtime (exclure commentaires de transition Phase 8.4)
    runtime_lines = [
        line
        for line in vnu_section.split("\n")
        if ("L. 336-1" in line or "L.336-1" in line) and not line.lstrip().startswith("#")
    ]
    assert not runtime_lines, "Phase 8.4 BLOQUANT REG : L.336-1 runtime résiduel section VNU :\n" + "\n".join(
        runtime_lines
    )


# ─── P0-002 — CGU archives rejected runtime PATCH ────────────────────────────


def test_phase84_is_valid_cgu_version_rejects_archive_by_default():
    """Phase 8.4 cardinal CNIL Article 7 : versions archive rejetées par défaut runtime PATCH."""
    from services.cgu_service import is_valid_cgu_version, reload_cgu_referentiel

    reload_cgu_referentiel()

    # Version actuel acceptée
    assert is_valid_cgu_version("1.0") is True, "Version 'actuel' doit être acceptée runtime"

    # Versions archive REJETÉES par défaut (cardinal CNIL Article 7)
    assert is_valid_cgu_version("0.9") is False, (
        "Phase 8.4 BLOQUANT : version archive '0.9' acceptée runtime (CNIL violation)"
    )
    assert is_valid_cgu_version("2.0") is False, "Phase 8.4 BLOQUANT : version archive '2.0' acceptée runtime"
    assert is_valid_cgu_version("2.1.0") is False, "Phase 8.4 BLOQUANT : version archive '2.1.0' acceptée runtime"


def test_phase84_is_valid_cgu_version_allows_archive_with_flag():
    """Phase 8.4 : `allow_archive=True` autorise archives (lookup audit historique)."""
    from services.cgu_service import is_valid_cgu_version

    # Versions archive acceptées avec flag explicite
    assert is_valid_cgu_version("0.9", allow_archive=True) is True
    assert is_valid_cgu_version("2.0", allow_archive=True) is True
    # Version actuel toujours acceptée
    assert is_valid_cgu_version("1.0", allow_archive=True) is True
    # Version inconnue rejetée même avec flag
    assert is_valid_cgu_version("99.99", allow_archive=True) is False


def test_phase84_is_known_cgu_version_helper():
    """Phase 8.4 : `is_known_cgu_version()` accepte actuel + archives (lookup audit)."""
    from services.cgu_service import is_known_cgu_version

    assert is_known_cgu_version("1.0") is True  # actuel
    assert is_known_cgu_version("2.0") is True  # archive postérieure
    assert is_known_cgu_version("0.9") is True  # archive antérieure
    assert is_known_cgu_version("forged") is False
    assert is_known_cgu_version(None) is False


def test_phase84_patch_org_consentement_rejects_archive_version(app_client):
    """Phase 8.4 cardinal CNIL : PATCH endpoint refuse cgu_version archive (CNIL Article 7)."""
    from models import Organisation

    client, SessionLocal = app_client
    db = SessionLocal()
    try:
        org = Organisation(nom="OrgPhase84", siren="887840001", actif=True)
        db.add(org)
        db.commit()
        org_id = org.id
    finally:
        db.close()

    # Version archive 2.0 (postérieure à 1.0 actuel) → rejet 422 cardinal CNIL
    resp = client.patch(
        f"/api/organisations/{org_id}/consentement",
        json={"consentement_dataconnect_global": True, "cgu_version": "2.0"},
        headers={"X-Org-Id": str(org_id)},
    )
    assert resp.status_code == 422, (
        f"Phase 8.4 BLOQUANT CNIL : cgu_version archive '2.0' devrait retourner 422, got {resp.status_code}"
    )


# ─── P0-003 — Helper ADR-020 wiring operat_export_service ────────────────────


def test_phase84_operat_export_service_uses_resolve_surface_helper():
    """Phase 8.4 P0 CR cardinal : `generate_operat_csv` utilise resolve_surface_for_operat_export()."""
    import inspect

    from services.operat_export_service import generate_operat_csv

    src = inspect.getsource(generate_operat_csv)
    assert "from regops.operat_export_helpers import resolve_surface_for_operat_export" in src, (
        "Phase 8.4 BLOQUANT : import resolve_surface_for_operat_export manquant"
    )
    assert "resolve_surface_for_operat_export(site)" in src, (
        "Phase 8.4 BLOQUANT : helper non appelé dans generate_operat_csv (orphelin ADR-020)"
    )


def test_phase84_operat_export_uses_s_ce_m2_when_site_has_it(app_client):
    """Phase 8.4 cardinal ADR-020 : si site.s_ce_m2 renseigné, export OPERAT utilise cette valeur."""
    from datetime import date

    from models import EntiteJuridique, Organisation, Portefeuille, Site, TypeSite
    from models import TertiaireEfa, TertiaireEfaBuilding
    from services.operat_export_service import generate_operat_csv

    _, SessionLocal = app_client
    db = SessionLocal()
    try:
        org = Organisation(nom="OrgPhase84CSV", siren="887840002", actif=True)
        db.add(org)
        db.flush()
        ej = EntiteJuridique(nom="EJ84CSV", siren="887840002", organisation_id=org.id)
        db.add(ej)
        db.flush()
        pf = Portefeuille(nom="PF84CSV", entite_juridique_id=ej.id)
        db.add(pf)
        db.flush()
        # Site avec s_ce_m2=1500 (priorité ADR-020) + tertiaire_area_m2=1000 (fallback)
        site = Site(
            nom="S84CSV",
            type=TypeSite.BUREAU,
            actif=True,
            portefeuille_id=pf.id,
            tertiaire_area_m2=1000.0,
            s_ce_m2=1500.0,
        )
        db.add(site)
        db.flush()
        # EFA + 1 building avec surface_m2=800 (différent de site)
        efa = TertiaireEfa(
            nom="EFA84",
            site_id=site.id,
            org_id=org.id,
        )
        db.add(efa)
        db.flush()
        bld = TertiaireEfaBuilding(efa_id=efa.id, surface_m2=800.0, usage_label="Bureau")
        db.add(bld)
        db.commit()
        org_id = org.id
    finally:
        db.close()

    db = SessionLocal()
    try:
        csv_str = generate_operat_csv(db, org_id, year=2026)
    finally:
        db.close()

    # Surface_m2 colonne CSV doit être 1500 (s_ce_m2 priorité ADR-020) — pas 1000 (tertiaire) ni 800 (building)
    assert "1500" in csv_str, (
        f"Phase 8.4 BLOQUANT ADR-020 : Surface_m2 colonne CSV doit être 1500 (s_ce_m2), got CSV : {csv_str[:500]}"
    )


def test_phase84_operat_export_falls_back_to_tertiaire_when_s_ce_null(app_client):
    """Phase 8.4 ADR-020 fallback : si s_ce_m2 None, utilise tertiaire_area_m2."""
    from models import EntiteJuridique, Organisation, Portefeuille, Site, TypeSite
    from models import TertiaireEfa, TertiaireEfaBuilding
    from services.operat_export_service import generate_operat_csv

    _, SessionLocal = app_client
    db = SessionLocal()
    try:
        org = Organisation(nom="OrgPhase84Fallback", siren="887840003", actif=True)
        db.add(org)
        db.flush()
        ej = EntiteJuridique(nom="EJ84FB", siren="887840003", organisation_id=org.id)
        db.add(ej)
        db.flush()
        pf = Portefeuille(nom="PF84FB", entite_juridique_id=ej.id)
        db.add(pf)
        db.flush()
        # Site SANS s_ce_m2, avec tertiaire_area_m2=1200
        site = Site(
            nom="S84FB",
            type=TypeSite.BUREAU,
            actif=True,
            portefeuille_id=pf.id,
            tertiaire_area_m2=1200.0,
            s_ce_m2=None,  # explicite NULL
        )
        db.add(site)
        db.flush()
        efa = TertiaireEfa(nom="EFA84FB", site_id=site.id, org_id=org.id)
        db.add(efa)
        db.flush()
        bld = TertiaireEfaBuilding(efa_id=efa.id, surface_m2=900.0, usage_label="Bureau")
        db.add(bld)
        db.commit()
        org_id = org.id
    finally:
        db.close()

    db = SessionLocal()
    try:
        csv_str = generate_operat_csv(db, org_id, year=2026)
    finally:
        db.close()

    # Surface_m2 doit être 1200 (tertiaire_area_m2 fallback) — pas 900 (building agrégat)
    assert "1200" in csv_str, "Phase 8.4 : fallback tertiaire_area_m2=1200 attendu, CSV doit contenir 1200"
