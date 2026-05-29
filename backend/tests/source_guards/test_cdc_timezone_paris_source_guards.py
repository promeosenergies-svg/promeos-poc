"""
PROMEOS — Source-guard : timezone Europe/Paris pour CDC / TURPE / horaires.

Sprint Énergie P0.S1a (2026-05-29, brief P2.2).

Doctrine : tout service énergétique qui manipule des horodatages métier
(classification slot TURPE, courbe de charge, agrégation horaire, DJU,
transitions DST mars/octobre) DOIT utiliser explicitement la timezone
`Europe/Paris` via `zoneinfo.ZoneInfo` ou un helper canonique.

Pourquoi ?
- Les meter readings sont stockés en UTC (`MeterReading.timestamp` naïf, par
  convention UTC en DB). La classification métier (HP/HC, jour ouvré, jour
  férié) DOIT se faire en heure locale française pour respecter les règles
  TURPE et CRE.
- Sans `Europe/Paris` explicite, un service qui tourne sous Docker UTC
  produit des décalages d'1 ou 2 h (été/hiver), faussant tous les KPI HP/HC.
- Les transitions DST (dernier dimanche mars / dernier dimanche octobre)
  doivent être gérées (collision DST détectée par alert_engine).

Ce source-guard vérifie :
1. Les fichiers énergétiques critiques (CDC, monitoring, TURPE, DJU)
   importent `Europe/Paris` (via ZoneInfo) OU délèguent à un helper.
2. Aucun service énergétique ne fait `datetime.now()` naïf sans timezone.
3. Aucun usage de `pytz` (deprecated — utiliser `zoneinfo` standard lib).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.fast

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND = REPO_ROOT / "backend"


# Fichiers énergie critiques qui DOIVENT déclarer Europe/Paris (ou déléguer
# explicitement à un service qui le fait).
ENERGY_TZ_CRITICAL_FILES = [
    "backend/services/ems/cdc_service.py",
    "backend/services/weather_dju_service.py",
    "backend/services/gas_weather_service.py",
    "backend/services/consumption_context_service.py",
    "backend/services/pilotage/roi_flex_ready.py",
]

# Helpers canoniques autorisés (alternative à ZoneInfo direct).
CANONICAL_TZ_HELPERS = [
    "TZ_PARIS",  # ems/cdc_service.py canonique
    "_TZ_PARIS",  # pilotage/roi_flex_ready.py
    "Europe/Paris",  # littéral explicite
    "ZoneInfo",  # import zoneinfo
    "europe_paris",  # snake_case helper potentiel
]


def _file_uses_europe_paris(path: Path) -> bool:
    """Vrai si le fichier référence Europe/Paris ou un helper canonique."""
    try:
        content = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, FileNotFoundError):
        return False
    return any(token in content for token in CANONICAL_TZ_HELPERS)


def _find_pytz_imports() -> list[tuple[str, int]]:
    """Cherche tous les imports de pytz (deprecated) dans backend/services/."""
    pattern = re.compile(r"^\s*(import\s+pytz|from\s+pytz)\b", re.MULTILINE)
    violations: list[tuple[str, int]] = []
    services_dir = BACKEND / "services"
    if not services_dir.exists():
        return violations
    for py_file in services_dir.rglob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError):
            continue
        for match in pattern.finditer(content):
            line_no = content[: match.start()].count("\n") + 1
            rel = py_file.relative_to(REPO_ROOT).as_posix()
            violations.append((rel, line_no))
    return violations


def _find_naive_datetime_now_in_energy() -> list[tuple[str, int, str]]:
    """Cherche `datetime.now()` sans argument timezone dans services énergie.

    Ne signale que les fichiers `services/ems/`, `services/electric_monitoring/`,
    `services/consumption_*`, et liés. Tolère `datetime.now(timezone.utc)` ou
    `datetime.now(TZ_PARIS)` ou similaire.
    """
    pattern = re.compile(r"datetime\.now\s*\(\s*\)")
    energy_dirs = [
        BACKEND / "services" / "ems",
        BACKEND / "services" / "electric_monitoring",
        BACKEND / "services" / "pilotage",
    ]
    energy_files = [
        BACKEND / "services" / "consumption_unified_service.py",
        BACKEND / "services" / "consumption_granularity_service.py",
        BACKEND / "services" / "consumption_context_service.py",
        BACKEND / "services" / "consumption_diagnostic.py",
        BACKEND / "services" / "weather_dju_service.py",
        BACKEND / "services" / "gas_weather_service.py",
        BACKEND / "services" / "load_profile_service.py",
        BACKEND / "services" / "baseline_service.py",
        BACKEND / "services" / "cdc_contract_simulator.py",
    ]
    targets: list[Path] = []
    for d in energy_dirs:
        if d.exists():
            targets.extend(d.rglob("*.py"))
    targets.extend(p for p in energy_files if p.exists())

    violations: list[tuple[str, int, str]] = []
    for py_file in targets:
        try:
            content = py_file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError):
            continue
        for match in pattern.finditer(content):
            line_no = content[: match.start()].count("\n") + 1
            snippet = content[max(0, match.start() - 20) : match.end() + 5]
            rel = py_file.relative_to(REPO_ROOT).as_posix()
            violations.append((rel, line_no, snippet.replace("\n", " ")[:80]))
    return violations


class TestCdcTimezoneParis:
    """Garde-fous timezone Europe/Paris sur la brique énergie."""

    def test_critical_energy_files_reference_europe_paris(self):
        """Les fichiers CDC / TURPE / DJU doivent déclarer Europe/Paris."""
        missing: list[str] = []
        for rel_path in ENERGY_TZ_CRITICAL_FILES:
            abs_path = REPO_ROOT / rel_path
            if not abs_path.exists():
                # Fichier absent : signaler explicitement (peut-être déplacé).
                missing.append(f"  {rel_path} → FICHIER MANQUANT (à vérifier)")
                continue
            if not _file_uses_europe_paris(abs_path):
                missing.append(
                    f"  {rel_path} → aucune référence Europe/Paris (ZoneInfo, TZ_PARIS, ou littéral 'Europe/Paris')"
                )
        if missing:
            msg = (
                "\n\n🔴 Fichiers énergie critiques sans timezone Europe/Paris "
                "(doctrine CDC/TURPE : classification métier en heure locale FR).\n\n"
                + "\n".join(missing)
                + "\n\nMigration : `from zoneinfo import ZoneInfo` + "
                "`TZ_PARIS = ZoneInfo('Europe/Paris')` puis "
                "`dt.astimezone(TZ_PARIS)` aux frontières de classification.\n"
            )
            pytest.fail(msg)

    def test_no_pytz_in_backend_services(self):
        """`pytz` est deprecated → utiliser `zoneinfo` (stdlib Python 3.9+)."""
        violations = _find_pytz_imports()
        if violations:
            msg = (
                "\n\n🔴 Import `pytz` détecté dans backend/services/ "
                "(deprecated, utiliser `zoneinfo` stdlib).\n\n"
                + "\n".join(f"  {rel}:{line}" for rel, line in violations)
                + "\n\nMigration : `from zoneinfo import ZoneInfo` "
                "(API quasi identique, pas de tz_offset).\n"
            )
            pytest.fail(msg)

    def test_no_naive_datetime_now_in_energy_services(self):
        """`datetime.now()` sans timezone produit du UTC sous Docker — incident historique
        Sprint 5b (cf. billing_engine/parameter_store.py:415).
        """
        violations = _find_naive_datetime_now_in_energy()
        if violations:
            msg = (
                "\n\n🔴 `datetime.now()` naïf dans services énergie "
                "(incident historique J-1 sous Docker UTC).\n\n"
                + "\n".join(f"  {rel}:{line} → « {snippet} »" for rel, line, snippet in violations)
                + "\n\nMigration : `datetime.now(timezone.utc)` ou "
                "`datetime.now(TZ_PARIS)` selon usage.\n"
            )
            pytest.fail(msg)
