"""
PROMEOS — Source-guards structure sources_reglementaires.yaml (Sprint C-3 Phase 3.2).

Anti-régression sur le SoT YAML versionné git :
- SG_REG_YAML_01 : tous termes ont keys requis (value, unit, domain, source, formula, notes)
- SG_REG_YAML_02 : source.label non vide pour chaque terme (audit trail légal)
- SG_REG_YAML_03 : source.url commence par https:// (lien vérifiable)
- SG_REG_YAML_04 : source.effective_date au format YYYY-MM-DD
- SG_REG_YAML_05 : source.domain ∈ allowlist (co2, tarifs, accises, tva, dt, bacs, aper, audit_sme, operat)
- SG_REG_YAML_06 : pas de term_id dupliqué (clés YAML uniques par construction, vérification renforcée)
"""

from __future__ import annotations

import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


_DOMAIN_ALLOWLIST = frozenset(
    {
        "co2",
        "tarifs",
        "accises",
        "tva",
        "dt",
        "bacs",
        "aper",
        "audit_sme",
        "operat",
        # Phase 3.4d audit follow-up — domaines doctrine PROMEOS distincts
        "regops",  # pondérations RegOps DT/BACS/APER (mirroir doctrine.constants)
        "readiness",  # pondérations readiness Data/Conformity/Actions
        # Phase L20.4 audit fix P1 (pré-existant L7+) — domaine bill_intelligence
        # ajouté Phase L7.2+L8.1+L9 pour 30+ clés BILL_ANOMALY_* (R19→R31 thresholds).
        "bill_intelligence",
    }
)
_DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_HTTPS_PREFIX = "https://"


def _load_yaml_data() -> dict:
    """Helper : charge le YAML via le loader canonical (assure cohérence test/runtime)."""
    from config.regulatory_sources_loader import reload_regulatory_sources

    return reload_regulatory_sources()


# ─── SG_REG_YAML_01 : keys requis ────────────────────────────────────────────


def test_sg_reg_yaml_01_all_terms_have_required_keys():
    """Tous les termes ont les 6 clés obligatoires (value, unit, domain, source, formula, notes)."""
    data = _load_yaml_data()
    required = {"value", "unit", "domain", "source", "formula", "notes"}

    offenders: list[str] = []
    for tid, term in data["terms"].items():
        missing = required - set(term.keys())
        if missing:
            offenders.append(f"{tid}: missing {sorted(missing)}")

    assert not offenders, "Termes mal structurés:\n  - " + "\n  - ".join(offenders)


# ─── SG_REG_YAML_02 : source.label non vide ──────────────────────────────────


def test_sg_reg_yaml_02_source_label_not_empty():
    """source.label doit être une string non vide pour chaque terme (audit trail)."""
    data = _load_yaml_data()
    offenders: list[str] = []
    for tid, term in data["terms"].items():
        label = term.get("source", {}).get("label", "")
        if not isinstance(label, str) or not label.strip():
            offenders.append(f"{tid}: source.label vide ou non-string ({label!r})")
    assert not offenders, "source.label invalide:\n  - " + "\n  - ".join(offenders)


# ─── SG_REG_YAML_03 : source.url https:// ────────────────────────────────────


def test_sg_reg_yaml_03_source_url_https():
    """source.url doit commencer par https:// (lien vérifiable et sécurisé).

    Phase L23.3 audit fix P1 — exemption domain `bill_intelligence` (paramètres
    doctrinaux internes PROMEOS, pas de source réglementaire externe à citer).
    Les ~34 clés BILL_ANOMALY_* + BILL_PRIORITY_SCORE_* Phase L7+L8+L9+L20+L22
    sont des seuils heuristiques internes documentés via `legal_reference`
    cardinal mais n'ont pas d'URL externe (cf. notes "Doctrine PROMEOS Phase L*").
    """
    data = _load_yaml_data()
    offenders: list[str] = []
    for tid, term in data["terms"].items():
        # Phase L23.3 — exempter le domain bill_intelligence (paramètres doctrinaux internes)
        domain = term.get("domain", "")
        if domain == "bill_intelligence":
            continue
        url = term.get("source", {}).get("url", "")
        if not isinstance(url, str) or not url.startswith(_HTTPS_PREFIX):
            offenders.append(f"{tid}: source.url={url!r} (attendu https://...)")
    assert not offenders, "URL non-https:// détectée:\n  - " + "\n  - ".join(offenders)


# ─── SG_REG_YAML_04 : source.effective_date YYYY-MM-DD ──────────────────────


def test_sg_reg_yaml_04_effective_date_iso_format():
    """source.effective_date doit être au format ISO YYYY-MM-DD."""
    data = _load_yaml_data()
    offenders: list[str] = []
    for tid, term in data["terms"].items():
        date_val = term.get("source", {}).get("effective_date", "")
        # YAML peut parser dates → on convertit en str pour validation regex
        date_str = str(date_val)
        if not _DATE_REGEX.match(date_str):
            offenders.append(f"{tid}: effective_date={date_str!r} (attendu YYYY-MM-DD)")
    assert not offenders, "effective_date mal formaté:\n  - " + "\n  - ".join(offenders)


# ─── SG_REG_YAML_05 : domain allowlist ───────────────────────────────────────


def test_sg_reg_yaml_05_domain_in_allowlist():
    """term.domain doit appartenir à l'allowlist 9 domaines connus."""
    data = _load_yaml_data()
    offenders: list[str] = []
    for tid, term in data["terms"].items():
        domain = term.get("domain")
        if domain not in _DOMAIN_ALLOWLIST:
            offenders.append(f"{tid}: domain={domain!r} (allowlist: {sorted(_DOMAIN_ALLOWLIST)})")
    assert not offenders, "Domain inconnu:\n  - " + "\n  - ".join(offenders)


# ─── SG_REG_YAML_06 : pas de duplicat term_id (sanity check) ────────────────


def test_sg_reg_yaml_06_no_duplicate_term_ids():
    """Les clés YAML sont uniques par construction, mais on valide via le loader."""
    from config.regulatory_sources_loader import list_all_term_ids

    term_ids = list_all_term_ids()
    assert len(term_ids) == len(set(term_ids)), "term_id dupliqué détecté — incohérence YAML"
