"""
PROMEOS — Tests cardinaux Phase D-3 Tier 2 (8 P1 critiques cumul audit deep Phase D).

Couvre :
- SEC-1 Path traversal CGU `compute_cgu_pdf_sha256` allowlist
- SEC-2 PII sanitizer SoT centralisé `services/security/pii_sanitizer.py`
- DOC-1 5 String→Enum runtime validators (Pilier 9 ADR-016 régularisé) :
    version_turpe / mode_traitement / mode_propriete / secteur / sub_meter_usage / dpe_class
- DOC-2 Anti-cycle D6 validator `Compteur.sub_meter_of_id`
- VAL-1 PCE/PRM format 14 chiffres `DeliveryPoint.code`
- VAL-2 tva_intra format `^FR\\d{11}$` `Organisation.tva_intra`

Sources audit Phase D : docs/audits/AUDIT_PHASE_D_COMPLET_2026_05_07.md.
"""

from __future__ import annotations

import pytest


# ─── SEC-1 Path traversal CGU ──────────────────────────────────────────────


def test_phase_d3_sec1_path_traversal_blocked_outside_allowlist(tmp_path):
    """SEC-1 : `compute_cgu_pdf_sha256` rejette chemin hors `<repo>/docs/cgu/`."""
    from services.cgu_service import compute_cgu_pdf_sha256

    # Fichier hors allowlist (tmp_path = système temp, pas repo/docs/cgu)
    rogue_pdf = tmp_path / "rogue.pdf"
    rogue_pdf.write_bytes(b"FAKE PDF")

    with pytest.raises(ValueError, match="Phase D-3 SEC-1 violation"):
        compute_cgu_pdf_sha256(str(rogue_pdf))


def test_phase_d3_sec1_path_traversal_blocks_etc_passwd():
    """SEC-1 : chemin absolu `/etc/passwd` rejeté (anti-oracle hash fichiers système)."""
    from services.cgu_service import compute_cgu_pdf_sha256

    with pytest.raises(ValueError, match="Phase D-3 SEC-1 violation"):
        compute_cgu_pdf_sha256("/etc/passwd")


# ─── SEC-2 PII sanitizer SoT centralisé ────────────────────────────────────


def test_phase_d3_sec2_pii_sanitizer_module_exists():
    """SEC-2 : module SoT centralisé `services/security/pii_sanitizer.py` existe."""
    from services.security import pii_sanitizer

    assert hasattr(pii_sanitizer, "PII_VALUE_PATTERNS")
    assert hasattr(pii_sanitizer, "SENSITIVE_KEY_PATTERNS")
    assert hasattr(pii_sanitizer, "SENSITIVE_KEY_NON_PII_ALLOWLIST")
    assert hasattr(pii_sanitizer, "HASH_KEY_PATTERNS")
    assert hasattr(pii_sanitizer, "sanitize_pii_value")
    assert hasattr(pii_sanitizer, "is_sensitive_key")
    assert hasattr(pii_sanitizer, "is_hash_key")


def test_phase_d3_sec2_pii_sanitizer_sot_unique_alias():
    """SEC-2 : anomaly_detector + audit_log_service pointent SoT unique (pas de duplication)."""
    from services.audit_log_service import _SENSITIVE_KEY_PATTERNS, _is_sensitive_key
    from services.bill_intelligence.anomaly_detector import _PII_PATTERNS, _sanitize_pii_label
    from services.security.pii_sanitizer import (
        PII_VALUE_PATTERNS,
        SENSITIVE_KEY_PATTERNS,
        is_sensitive_key,
        sanitize_pii_value,
    )

    # Identité d'objet (alias direct, pas re-déclaration)
    assert _PII_PATTERNS is PII_VALUE_PATTERNS
    assert _SENSITIVE_KEY_PATTERNS is SENSITIVE_KEY_PATTERNS
    assert _sanitize_pii_label is sanitize_pii_value
    assert _is_sensitive_key is is_sensitive_key


def test_phase_d3_sec2_pii_redaction_email_iban_siren():
    """SEC-2 : sanitization couvre email + IBAN + SIREN/SIRET (cumul Phase 8.2)."""
    from services.security.pii_sanitizer import sanitize_pii_value

    cases = [
        ("contact@client.fr", "contact@client.fr"),
        ("FR76 1234 5678 9012 3456 7890 123", "FR76 1234"),
        ("SIREN 552032534 dormant", "552032534"),
        ("SIRET 12345678901234 dormant", "12345678901234"),
        ("+33 6 12 34 56 78 contact", "+33 6"),
    ]
    for label, pii in cases:
        sanitized = sanitize_pii_value(label)
        assert pii not in sanitized, f"PII {pii!r} non redacted dans {sanitized!r}"
        assert "<PII_REDACTED>" in sanitized


# ─── DOC-1 String→Enum runtime validators ──────────────────────────────────


def test_phase_d3_doc1_version_turpe_strict_enum():
    """DOC-1 : `version_turpe` accepte uniquement TURPE_6/TURPE_7."""
    from models.patrimoine import DeliveryPoint

    dp = DeliveryPoint(code="78999000000001", site_id=1)
    dp.version_turpe = "TURPE_6"
    dp.version_turpe = "TURPE_7"

    with pytest.raises(ValueError, match="version_turpe"):
        dp.version_turpe = "TURPE_8"


def test_phase_d3_doc1_mode_traitement_strict_enum():
    """DOC-1 : `mode_traitement` accepte uniquement smart/traditionnel/telereleve/manuel."""
    from models.patrimoine import DeliveryPoint

    dp = DeliveryPoint(code="78999000000002", site_id=1)
    dp.mode_traitement = "smart"
    dp.mode_traitement = "manuel"

    with pytest.raises(ValueError, match="mode_traitement"):
        dp.mode_traitement = "rogue_mode"


def test_phase_d3_doc1_mode_propriete_strict_enum():
    """DOC-1 : `mode_propriete` réutilise EfaRole (PROPRIETAIRE/LOCATAIRE/MANDATAIRE)."""
    from models.enums import TypeSite
    from models.site import Site

    s = Site(nom="X", type=TypeSite.BUREAU)
    s.mode_propriete = "proprietaire"
    s.mode_propriete = "locataire"
    s.mode_propriete = "mandataire"

    with pytest.raises(ValueError, match="mode_propriete"):
        s.mode_propriete = "owner"  # English not allowed


def test_phase_d3_doc1_secteur_strict_typologie():
    """DOC-1 : `secteur` Org réutilise `Typologie` Enum."""
    from models import Organisation

    org = Organisation(nom="X", siren="999123456")
    org.secteur = "tertiaire_prive"
    org.secteur = "industrie"
    org.secteur = "commerce_retail"

    with pytest.raises(ValueError, match="secteur"):
        org.secteur = "tertiaire_bureaux"  # legacy non canonique


def test_phase_d3_doc1_dpe_class_strict_enum():
    """DOC-1 : `dpe_class` réutilise `DpeClasseEnergie` (A-G + VIERGE)."""
    from models.batiment import Batiment

    b = Batiment(site_id=1, nom="Aile", surface_m2=1000.0)
    b.dpe_class = "A"
    b.dpe_class = "G"
    b.dpe_class = "vierge"

    with pytest.raises(ValueError, match="dpe_class"):
        b.dpe_class = "Z"


def test_phase_d3_doc1_sub_meter_usage_strict_enum():
    """DOC-1 : `sub_meter_usage` strict `SubMeterUsageEnum`."""
    from models.compteur import Compteur
    from models.enums import TypeCompteur

    c = Compteur(type=TypeCompteur.ELECTRICITE, site_id=1)
    c.sub_meter_usage = "CVC"
    c.sub_meter_usage = "IT"
    c.sub_meter_usage = "PROCESS"

    with pytest.raises(ValueError, match="sub_meter_usage"):
        c.sub_meter_usage = "Heating"


# ─── DOC-2 Anti-cycle D6 validator ─────────────────────────────────────────


def test_phase_d3_doc2_anti_cycle_self_reference_rejected():
    """DOC-2 : `Compteur.sub_meter_of_id == Compteur.id` rejeté (auto-référence)."""
    from models.compteur import Compteur
    from models.enums import TypeCompteur

    c = Compteur(type=TypeCompteur.ELECTRICITE, site_id=1, numero_serie="X")
    c.id = 42
    with pytest.raises(ValueError, match="auto-référence"):
        c.sub_meter_of_id = 42


def test_phase_d3_doc2_anti_cycle_different_id_ok():
    """DOC-2 : `sub_meter_of_id` différent de `id` accepté."""
    from models.compteur import Compteur
    from models.enums import TypeCompteur

    c = Compteur(type=TypeCompteur.ELECTRICITE, site_id=1, numero_serie="X")
    c.id = 42
    c.sub_meter_of_id = 41  # parent différent
    assert c.sub_meter_of_id == 41


# ─── VAL-1 PCE/PRM format 14 chiffres ──────────────────────────────────────


def test_phase_d3_val1_pce_prm_3_formats_canoniques():
    """VAL-1 cardinal : 3 formats canoniques PRM/PCE (cross-check sources officielles).

    Sources officielles vérifiées audit regulatory-expert agent SDK :
    - DISTRIBUTION_14 : `\\d{14}` — CRE Délib. 2025-161 du 19/06/2025 (JORFTEXT000051807406)
    - DISTRIBUTION_GI : `GI\\d{6}` — CRE 2025-161 (gros industriel GRDF, longueur low-confidence)
    - TRANSPORT_PIR   : `IR\\d{4}` — smart.grtgaz.com URLs publiques (PIR GRTgaz/NaTran)

    ⚠️ Matrice v1 §4.6.C label 'TRANSPORT_GI6' corrigé Phase D-3 Tier 2 : `GI\\d{6}`
    est PCE distribution gros indus GRDF, PAS transport. Format transport = `IR\\d{4}`.
    """
    from models.patrimoine import DeliveryPoint

    # DISTRIBUTION_14 — Enedis PRM élec OU GRDF PCE résidentiel/petit pro (CRE 2025-161)
    DeliveryPoint(code="14999000000001", site_id=1)
    DeliveryPoint(code="22555444333222", site_id=1)

    # DISTRIBUTION_GI — GRDF gros industriel distribution (CRE 2025-161)
    DeliveryPoint(code="GI123456", site_id=1)
    DeliveryPoint(code="GI000001", site_id=1)

    # TRANSPORT_PIR — Point Interconnexion Réseau GRTgaz/NaTran (smart.grtgaz.com)
    DeliveryPoint(code="IR0011", site_id=1)
    DeliveryPoint(code="IR0015", site_id=1)
    DeliveryPoint(code="IR0053", site_id=1)
    DeliveryPoint(code="IR9999", site_id=1)

    # Rejets : formats invalides
    with pytest.raises(ValueError, match="VAL-1.*PRM/PCE"):
        DeliveryPoint(code="ABC123", site_id=1)

    with pytest.raises(ValueError, match="VAL-1.*PRM/PCE"):
        DeliveryPoint(code="12345", site_id=1)  # trop court

    with pytest.raises(ValueError, match="VAL-1.*PRM/PCE"):
        DeliveryPoint(code="GI12345", site_id=1)  # GI + 5 chiffres (incomplet)

    with pytest.raises(ValueError, match="VAL-1.*PRM/PCE"):
        DeliveryPoint(code="GI1234567", site_id=1)  # GI + 7 chiffres (excédent)

    with pytest.raises(ValueError, match="VAL-1.*PRM/PCE"):
        DeliveryPoint(code="IR123", site_id=1)  # IR + 3 chiffres (incomplet)

    with pytest.raises(ValueError, match="VAL-1.*PRM/PCE"):
        DeliveryPoint(code="IR12345", site_id=1)  # IR + 5 chiffres (excédent)

    with pytest.raises(ValueError, match="VAL-1.*PRM/PCE"):
        DeliveryPoint(code="LI0011", site_id=1)  # `LI` non canonique (verdict agent SDK)


# ─── VAL-2 tva_intra format ^FR\d{11}$ ─────────────────────────────────────


def test_phase_d3_val2_tva_intra_fr_format_strict():
    """VAL-2 : tva_intra format strict `^FR\\d{11}$`."""
    from models import Organisation

    org = Organisation(nom="X", siren="999111222")
    org.tva_intra = "FR12345678901"  # 13 chars OK

    with pytest.raises(ValueError, match="tva_intra"):
        org.tva_intra = "FR123456789"  # trop court

    with pytest.raises(ValueError, match="tva_intra"):
        org.tva_intra = "12345678901"  # sans FR

    with pytest.raises(ValueError, match="tva_intra"):
        org.tva_intra = "FRabcdefghijk"  # lettres
