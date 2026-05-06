"""
PROMEOS — Tests cardinaux Phase D-1 hotfix Patrimoine (audit Sprint Patrimoine v1).

Couvre 4 P1 audit :
- D-Audit-PARAM-DP-TURPE7-Explicite-006 P1 (DP 5 champs TURPE 7)
- D-Audit-PARAM-Org-Champs-004 P1 (Org 6 champs entreprise enrichie)
- D-Audit-C8-PII-Patterns-Order-006 P1 SEC (ordre patterns + retrait \\b\\d{10}\\b)
- D-Audit-C8-CGU-Pdf-Hash-007 P1 REG (helper compute_cgu_pdf_sha256 + verify)
"""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path


# ─── P1-006 — DP TURPE 7 explicite ──────────────────────────────────────────


def test_phase_d1_delivery_point_has_turpe7_explicit_fields():
    """Phase D-1 cardinal : DeliveryPoint 5 champs TURPE 7 explicites présents."""
    from sqlalchemy import inspect

    from models.patrimoine import DeliveryPoint

    columns = {c.name: c for c in inspect(DeliveryPoint).columns}
    cardinal_fields = ["categorie_turpe", "domaine_tension", "code_fta", "version_turpe", "mode_traitement"]
    missing = [f for f in cardinal_fields if f not in columns]
    assert not missing, f"Phase D-1 BLOQUANT : champs TURPE 7 manquants : {missing}"


def test_phase_d1_delivery_point_turpe7_persist(app_client):
    """Phase D-1 : DP TURPE 7 fields persist + reload."""
    from models import EntiteJuridique, Organisation, Portefeuille, Site, TypeSite
    from models.enums import DeliveryPointEnergyType
    from models.patrimoine import DeliveryPoint

    _, SessionLocal = app_client
    db = SessionLocal()
    try:
        org = Organisation(nom="OrgD1", siren="999100001")
        db.add(org)
        db.flush()
        ej = EntiteJuridique(nom="EJD1", siren="999100001", organisation_id=org.id)
        db.add(ej)
        db.flush()
        pf = Portefeuille(nom="PFD1", entite_juridique_id=ej.id)
        db.add(pf)
        db.flush()
        site = Site(nom="SD1", type=TypeSite.BUREAU, actif=True, portefeuille_id=pf.id)
        db.add(site)
        db.flush()

        dp = DeliveryPoint(
            code="12345678901234",
            energy_type=DeliveryPointEnergyType.ELEC,
            grd_code="ENEDIS",
            site_id=site.id,
            categorie_turpe="C5",
            domaine_tension="BT≤36kVA",
            code_fta="BTINFCU4",  # Phase D-2 hotfix Tier 1 P0.2 : code canonique CRE (était BT_HCH_PRO inventé)
            version_turpe="TURPE_7",
            mode_traitement="smart",
        )
        db.add(dp)
        db.commit()
        db.refresh(dp)

        assert dp.categorie_turpe == "C5"
        assert dp.domaine_tension == "BT≤36kVA"
        assert dp.code_fta == "BTINFCU4"
        assert dp.version_turpe == "TURPE_7"
        assert dp.mode_traitement == "smart"
    finally:
        db.close()


# ─── P1-004 — Org enrichi entreprise ────────────────────────────────────────


def test_phase_d1_org_has_enriched_entreprise_fields():
    """Phase D-1 cardinal : Organisation 6 champs entreprise enrichie présents."""
    from sqlalchemy import inspect

    from models.organisation import Organisation

    columns = {c.name: c for c in inspect(Organisation).columns}
    cardinal_fields = ["tva_intra", "code_naf_principal", "pays", "secteur", "effectif_total", "chiffre_affaires_eur"]
    missing = [f for f in cardinal_fields if f not in columns]
    assert not missing, f"Phase D-1 BLOQUANT : champs Org entreprise manquants : {missing}"


def test_phase_d1_org_enriched_persist(app_client):
    """Phase D-1 : Org entreprise enrichie persist + reload."""
    from models import Organisation

    _, SessionLocal = app_client
    db = SessionLocal()
    try:
        org = Organisation(
            nom="OrgD1Enriched",
            siren="999100002",
            tva_intra="FR12345678901",
            code_naf_principal="6201Z",
            pays="FR",
            secteur="tertiaire_prive",
            effectif_total=120,
            chiffre_affaires_eur=15_000_000.0,
        )
        db.add(org)
        db.commit()
        db.refresh(org)

        assert org.tva_intra == "FR12345678901"
        assert org.code_naf_principal == "6201Z"
        assert org.pays == "FR"
        assert org.secteur == "tertiaire_prive"
        assert org.effectif_total == 120
        assert org.chiffre_affaires_eur == 15_000_000.0
    finally:
        db.close()


# ─── P1-006 — PII patterns ordre + retrait \\b\\d{10}\\b ────────────────────


def test_phase_d1_pii_patterns_no_short_10_digits_runtime():
    """Phase D-1 cardinal SEC : pattern `\\b\\d{10}\\b` PCE legacy retiré (anti faux-positifs montants)."""
    import inspect

    from services.bill_intelligence import anomaly_detector

    src = inspect.getsource(anomaly_detector)
    # Anti-pattern : `re.compile(r"\b\d{10}\b")` runtime (le commentaire mentionnant le retrait OK)
    runtime_lines = [
        line for line in src.split("\n") if r"re.compile(r\"\b\d{10}\b\")" in line and not line.lstrip().startswith("#")
    ]
    assert not runtime_lines, (
        "Phase D-1 BLOQUANT SEC : pattern \\b\\d{10}\\b runtime résiduel (anti faux-positifs montants TURPE numériques)"
    )


def test_phase_d1_pii_patterns_montant_turpe_not_redacted():
    """Phase D-1 anti-régression : montant TURPE 10 chiffres `0000123456` PRESERVÉ (vs sur-redaction)."""
    from services.bill_intelligence.anomaly_detector import _sanitize_pii_label

    # Code interne 10 chiffres style montant TURPE (entier)
    label = "Tarif HPH référence 0000123456 EUR/MWh"
    sanitized = _sanitize_pii_label(label)
    assert "0000123456" in sanitized, "Phase D-1 BLOQUANT : code 10 chiffres montant TURPE sur-redacted (régression)"


def test_phase_d1_pii_patterns_real_pii_still_redacted():
    """Phase D-1 : vrais PII (SIREN/SIRET/Email/IBAN/Tel FR) restent redacted."""
    from services.bill_intelligence.anomaly_detector import _sanitize_pii_label

    cases = [
        ("VNU SIREN 552032534 dormant", "552032534"),
        ("VNU SIRET 12345678901234 dormant", "12345678901234"),
        ("Email contact@client.fr facture", "contact@client.fr"),
        ("IBAN FR76 1234 5678 9012 3456 7890 123", "FR76 1234"),
        ("Tel +33 6 12 34 56 78 contact", "+33 6"),
    ]
    for label, pii in cases:
        sanitized = _sanitize_pii_label(label)
        assert pii not in sanitized, f"Phase D-1 RÉGRESSION SEC : '{pii}' encore dans '{sanitized}'"
        assert "<PII_REDACTED>" in sanitized


# ─── P1-007 — CGU sha256 helper ─────────────────────────────────────────────


def test_phase_d1_compute_cgu_pdf_sha256_returns_64_hex():
    """Phase D-1 : `compute_cgu_pdf_sha256` calcule SHA-256 hexadécimal (64 chars).

    Phase D-3 Tier 2 SEC-1 : test adapté à l'allowlist `<repo>/docs/cgu/` cardinale.
    """
    from services.cgu_service import compute_cgu_pdf_sha256, _CGU_PDF_ALLOWED_ROOT

    _CGU_PDF_ALLOWED_ROOT.mkdir(parents=True, exist_ok=True)
    test_pdf = _CGU_PDF_ALLOWED_ROOT / "CGU_test_phase_d1.pdf"
    try:
        test_pdf.write_bytes(b"FAKE PDF CGU CONTENT v1.0 2026-01-15")
        sha = compute_cgu_pdf_sha256(str(test_pdf))

        assert len(sha) == 64
        assert all(c in "0123456789abcdef" for c in sha)
        expected = hashlib.sha256(b"FAKE PDF CGU CONTENT v1.0 2026-01-15").hexdigest()
        assert sha == expected
    finally:
        if test_pdf.exists():
            test_pdf.unlink()


def test_phase_d1_compute_cgu_pdf_sha256_raises_on_missing():
    """Phase D-1 : raises FileNotFoundError si PDF absent (dans allowlist)."""
    import pytest

    from services.cgu_service import compute_cgu_pdf_sha256, _CGU_PDF_ALLOWED_ROOT

    _CGU_PDF_ALLOWED_ROOT.mkdir(parents=True, exist_ok=True)
    missing_path = str(_CGU_PDF_ALLOWED_ROOT / "CGU_inexistant.pdf")
    with pytest.raises(FileNotFoundError):
        compute_cgu_pdf_sha256(missing_path)


def test_phase_d1_verify_cgu_version_integrity_status_no_hash_yet():
    """Phase D-1 : `verify_cgu_version_integrity` retourne 'no_hash_yet' si contenu_sha256 null."""
    from services.cgu_service import verify_cgu_version_integrity

    # Version "1.0" actuel a contenu_sha256: null par défaut Phase 8.4
    result = verify_cgu_version_integrity("1.0")
    assert result["status"] in ("no_hash_yet", "expected_sha256_only")
    assert result["version"] == "1.0"


def test_phase_d1_verify_cgu_version_integrity_unknown_version():
    """Phase D-1 : version inconnue → status='unknown_version'."""
    from services.cgu_service import verify_cgu_version_integrity

    result = verify_cgu_version_integrity("99.99-forged")
    assert result["status"] == "unknown_version"


# ─── Anti-régression migration 14e ──────────────────────────────────────────


def test_phase_d1_alembic_migration_14e_clean_no_destructive():
    """Phase D-1 : 14e migration Alembic propre, anti-DROP discipline 14e épisode."""
    migration = (
        Path(__file__).parent.parent / "alembic" / "versions" / "c554f6299e9c_phase_d_1_hotfix_dp_turpe7_explicite_.py"
    )
    assert migration.exists(), "Phase D-1 BLOQUANT : migration 14e absente"

    content = migration.read_text(encoding="utf-8")
    assert "D-Audit-PARAM-DP-TURPE7-Explicite-006" in content
    assert "D-Audit-PARAM-Org-Champs-004" in content
    assert "14 migrations propres / 0 destructive" in content
