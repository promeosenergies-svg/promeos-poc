"""
PROMEOS — Source-guards structure eld_gaz_referentiel.yaml (Sprint C-3 Phase 3.6).

Anti-régression sur le SoT YAML versionné git :
- SG_ELD_01 : `eld:` key présente + tous codes uniques
- SG_ELD_02 : GRDF présent (référence nationale obligatoire)
- SG_ELD_03 : chaque entrée a 7 keys requises
- SG_ELD_04 : type ∈ allowlist {"GRD_NATIONAL", "ELD_LOCALE"}
- SG_ELD_05 : site_web (si présent) commence par https://
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


_TYPE_ALLOWLIST = frozenset({"GRD_NATIONAL", "ELD_LOCALE"})
_REQUIRED_KEYS = {"code", "label", "type", "perimetre", "site_web", "contact_consentement", "notes"}


def _load_eld_data() -> dict:
    from config.eld_gaz_loader import reload_eld_gaz

    return reload_eld_gaz()


def test_sg_eld_01_eld_key_present_and_codes_unique():
    """`eld` key présent + clés YAML uniques (par construction)."""
    data = _load_eld_data()
    assert "eld" in data
    eld_dict = data["eld"]
    assert isinstance(eld_dict, dict)
    # Cohérence : eld[code]["code"] == code (sanity)
    for key, entry in eld_dict.items():
        assert entry.get("code") == key, f"Mismatch key={key} vs entry.code={entry.get('code')}"


def test_sg_eld_02_grdf_present_as_grd_national():
    """GRDF est obligatoirement présent et de type GRD_NATIONAL."""
    data = _load_eld_data()
    assert "GRDF" in data["eld"], "GRDF absent du référentiel ELD (référence nationale obligatoire)"
    assert data["eld"]["GRDF"]["type"] == "GRD_NATIONAL"


def test_sg_eld_03_all_entries_have_required_keys():
    """Chaque entrée ELD doit avoir 7 keys requises."""
    data = _load_eld_data()
    offenders = []
    for code, entry in data["eld"].items():
        missing = _REQUIRED_KEYS - set(entry.keys())
        if missing:
            offenders.append(f"{code}: missing {sorted(missing)}")
    assert not offenders, "ELD mal structurées:\n  - " + "\n  - ".join(offenders)


def test_sg_eld_04_type_in_allowlist():
    """type ∈ {GRD_NATIONAL, ELD_LOCALE}."""
    data = _load_eld_data()
    offenders = []
    for code, entry in data["eld"].items():
        t = entry.get("type")
        if t not in _TYPE_ALLOWLIST:
            offenders.append(f"{code}: type={t!r} (allowlist: {sorted(_TYPE_ALLOWLIST)})")
    assert not offenders, "Type ELD inconnu:\n  - " + "\n  - ".join(offenders)


def test_sg_eld_05_site_web_https_when_not_null():
    """Si site_web est défini, il doit commencer par https://."""
    data = _load_eld_data()
    offenders = []
    for code, entry in data["eld"].items():
        site = entry.get("site_web")
        if site is None:
            continue  # null acceptable
        if not isinstance(site, str) or not site.startswith("https://"):
            offenders.append(f"{code}: site_web={site!r} (attendu https:// ou null)")
    assert not offenders, "ELD site_web non-https://:\n  - " + "\n  - ".join(offenders)
