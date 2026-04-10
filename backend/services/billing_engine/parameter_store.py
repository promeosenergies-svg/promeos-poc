"""
PROMEOS — ParameterStore

Source unique de vérité pour tous les paramètres réglementés du moteur
shadow billing : TURPE, ATRD, ATRT, accises, CTA, CEE, TVA.

Principes :
- UN SEUL chemin de résolution : ParameterStore.get(code, at_date, scope)
- Versioning par (code, scope, valid_from) avec sélection par date d'effet
- Priorité : DB (regulated_tariffs) → YAML (tarifs_reglementaires.yaml)
- Jamais de valeur en dur dans ce module (fallback "0.0 + warning" plutôt
  qu'une fausse valeur hardcodée qui masque un trou référentiel)
- Audit trail sur chaque lookup : source, date d'effet retenue, scope résolu

Compatibilité :
- Les helpers historiques de config/tarif_loader.py continuent de fonctionner
  en déléguant à ParameterStore (transparent pour les appelants).
- Les valeurs retournées restent en EUR/kWh (pas EUR/MWh) pour rester
  compatibles avec le code existant.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Codes connus du référentiel — documentés pour éviter les fautes de frappe.
# Tout code qui n'est pas dans cette liste déclenche un warning au premier lookup.
KNOWN_CODES = frozenset(
    {
        # TURPE énergie (EUR/kWh)
        "TURPE_ENERGIE_C5_BT",
        "TURPE_ENERGIE_C4_BT",
        "TURPE_ENERGIE_C3_HTA",
        # TURPE gestion (EUR/mois)
        "TURPE_GESTION_C5_BT",
        "TURPE_GESTION_C4_BT",
        "TURPE_GESTION_C3_HTA",
        # Acheminement gaz (EUR/kWh)
        "ATRD_GAZ",
        "ATRT_GAZ",
        # Accises (EUR/kWh)
        "ACCISE_ELEC",
        "ACCISE_ELEC_T1",  # ménages/assimilés ≤ 250 MWh
        "ACCISE_ELEC_T2",  # PME 250 MWh – 1 GWh
        "ACCISE_ELEC_HP",  # haute puissance
        "ACCISE_GAZ",
        # CTA (ratio, p. ex. 0.15 = 15%)
        "CTA_ELEC_DIST_RATE",
        "CTA_ELEC_TRANS_RATE",
        "CTA_GAZ_DIST_RATE",
        "CTA_GAZ_TRANS_RATE",
        # CEE (coefficient obligation kWhc/kWh et prix hypothétique EUR/MWhc)
        "CEE_ELEC_COEFF",
        "CEE_GAZ_COEFF",
        "CEE_PRICE_EUR_PER_MWHC",
        # TVA (ratio)
        "TVA_NORMALE",
        "TVA_REDUITE",
        # Prix de référence fallback (EUR/kWh)
        "DEFAULT_PRICE_ELEC",
        "DEFAULT_PRICE_GAZ",
    }
)


@dataclass(frozen=True)
class ParameterResolution:
    """Résultat d'une résolution : valeur + trace d'audit."""

    code: str
    value: float
    source: str  # "db" | "yaml" | "missing"
    source_ref: Optional[str]  # référence réglementaire (arrêté, délibération CRE)
    valid_from: Optional[date]
    valid_to: Optional[date]
    scope: dict[str, str]  # scope effectivement résolu

    def to_trace(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "value": self.value,
            "source": self.source,
            "source_ref": self.source_ref,
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
            "scope": self.scope,
        }


# ── YAML loader ────────────────────────────────────────────────────────────
# Cache unique partagé avec `config.tarif_loader.load_tarifs` — même fichier,
# mêmes sémantiques, une seule source de vérité. Évite que `reload_tarifs()`
# côté legacy laisse un ParameterStore stale en tests.


def _load_yaml() -> dict:
    try:
        from config.tarif_loader import load_tarifs

        return load_tarifs() or {}
    except Exception as exc:
        logger.warning("ParameterStore: YAML loader indisponible (%s)", exc)
        return {}


def reload_yaml_cache() -> None:
    """Force un rechargement du YAML (tests, hot-patch)."""
    try:
        from config.tarif_loader import reload_tarifs

        reload_tarifs()
    except Exception as exc:
        logger.debug("ParameterStore.reload_yaml_cache: %s", exc)


# ── Helpers de normalisation ──────────────────────────────────────────────
def _coerce_date(value: Any) -> Optional[date]:
    """Normalise une date (str ISO, datetime, date) en date pure."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            logger.warning("ParameterStore: date invalide '%s'", value)
            return None
    return None


def _period_contains(valid_from: Optional[date], valid_to: Optional[date], at: date) -> bool:
    """True si `at` est dans [valid_from, valid_to] (bornes incluses)."""
    if valid_from and at < valid_from:
        return False
    if valid_to and at > valid_to:
        return False
    return True


# ── Table de résolution YAML → code ───────────────────────────────────────
# Chaque entrée retourne une liste de candidats (dict YAML) et la clé à lire.
# On parcourt les candidats, on garde ceux dont la période contient `at_date`,
# et on retient celui dont `valid_from` est le plus récent (cas d'entrées
# successives type "accise_gaz_2024" / "accise_gaz_2025_jan" / "accise_gaz").
def _yaml_candidates(code: str, tarifs: dict) -> list[tuple[dict, str]]:
    """Retourne une liste (entry_dict, value_key) pour un code donné."""
    # TURPE (gère TURPE 6 et TURPE 7 simultanément)
    if code.startswith("TURPE_ENERGIE_"):
        seg = code.replace("TURPE_ENERGIE_", "")
        out = []
        for root_key in ("turpe_6", "turpe"):
            root = tarifs.get(root_key)
            if root and "segments" in root and seg in root["segments"]:
                entry = dict(root["segments"][seg])
                entry["valid_from"] = root.get("valid_from")
                entry["valid_to"] = root.get("valid_to")
                entry["source"] = root.get("source")
                out.append((entry, "energie_eur_kwh"))
        return out

    if code.startswith("TURPE_GESTION_"):
        seg = code.replace("TURPE_GESTION_", "")
        out = []
        for root_key in ("turpe_6", "turpe"):
            root = tarifs.get(root_key)
            if root and "segments" in root and seg in root["segments"]:
                entry = dict(root["segments"][seg])
                entry["valid_from"] = root.get("valid_from")
                entry["valid_to"] = root.get("valid_to")
                entry["source"] = root.get("source")
                out.append((entry, "gestion_eur_mois"))
        return out

    # Accises élec (gère 2024, 2026_t1, 2026_t2, accise_elec "courant")
    if code == "ACCISE_ELEC" or code == "ACCISE_ELEC_T2":
        return [
            (tarifs.get("accise_elec_2024_pme", {}), "rate_eur_kwh"),
            (tarifs.get("accise_elec_2026_t2", {}), "rate_eur_kwh"),
            (tarifs.get("accise_elec", {}), "rate_eur_kwh"),
        ]
    if code == "ACCISE_ELEC_T1":
        return [
            (tarifs.get("accise_elec_2024_menages", {}), "rate_eur_kwh"),
            (tarifs.get("accise_elec_2026_t1", {}), "rate_eur_kwh"),
        ]
    if code == "ACCISE_ELEC_HP":
        return [
            (tarifs.get("accise_elec_2024_haute_puissance", {}), "rate_eur_kwh"),
        ]

    # Accise gaz (2024, 2025 jan, 2025 aout, 2026)
    if code == "ACCISE_GAZ":
        return [
            (tarifs.get("accise_gaz_2024", {}), "rate_eur_kwh"),
            (tarifs.get("accise_gaz_2025_jan", {}), "rate_eur_kwh"),
            (tarifs.get("accise_gaz_2025_aout", {}), "rate_eur_kwh"),
            (tarifs.get("accise_gaz", {}), "rate_eur_kwh"),
        ]

    # Acheminement gaz
    if code == "ATRD_GAZ":
        return [(tarifs.get("atrd_gaz", {}), "rate_eur_kwh")]
    if code == "ATRT_GAZ":
        return [(tarifs.get("atrt_gaz", {}), "rate_eur_kwh")]

    # CTA — ratio (taux_pct / 100), énumère les historiques + courant
    if code in ("CTA_ELEC_DIST_RATE", "CTA_ELEC_TRANS_RATE", "CTA_GAZ_DIST_RATE", "CTA_GAZ_TRANS_RATE"):
        cta_subkey = {
            "CTA_ELEC_DIST_RATE": "elec",
            "CTA_ELEC_TRANS_RATE": "elec_transport",
            "CTA_GAZ_DIST_RATE": "gaz",
            "CTA_GAZ_TRANS_RATE": "gaz",
        }[code]
        out: list[tuple[dict, str]] = []
        # Les racines possibles sont listées dans l'ordre chronologique ; le
        # candidat dont la période contient at_date sera sélectionné par
        # _select_best_candidate.
        for root_key in ("cta_2021", "cta"):
            entry = dict(tarifs.get(root_key, {}).get(cta_subkey, {}))
            if "taux_pct" in entry:
                entry["_ratio"] = entry["taux_pct"] / 100.0
                out.append((entry, "_ratio"))
        return out

    # TVA
    if code == "TVA_NORMALE":
        entry = tarifs.get("tva", {}).get("normale", {})
        return [(entry, "taux")]
    if code == "TVA_REDUITE":
        # La TVA réduite (5,5%) a été supprimée le 1/08/2025 (LFI 2025).
        # On la modélise comme deux entrées : l'ancienne avec valid_to explicite,
        # et la nouvelle qui pointe vers le taux normal depuis le 1/08/2025.
        reduite = dict(tarifs.get("tva", {}).get("reduite", {}))
        normale = tarifs.get("tva", {}).get("normale", {})
        supprime_au = reduite.get("supprime_au")
        candidates = []
        if "taux" in reduite:
            # Ancienne version : valid_to = supprime_au - 1 jour
            ancien = dict(reduite)
            if supprime_au:
                # Le YAML exprime supprime_au comme "première date sans effet",
                # donc valid_to = supprime_au (exclusive). On garde la convention
                # inclusive en retranchant 1 jour.
                sup_d = _coerce_date(supprime_au)
                if sup_d:
                    ancien["valid_to"] = (sup_d - timedelta(days=1)).isoformat()
                    ancien["valid_from"] = ancien.get("valid_from") or "2000-01-01"
            candidates.append((ancien, "taux"))
        if supprime_au and "taux" in normale:
            # Nouvelle version : à partir de supprime_au, on pointe sur le normal
            nouveau = {
                "taux": normale["taux"],
                "valid_from": supprime_au,
                "valid_to": None,
                "source": reduite.get("source") or "LFI 2025 — suppression taux réduit",
            }
            candidates.append((nouveau, "taux"))
        return candidates

    # Prix de référence
    if code == "DEFAULT_PRICE_ELEC":
        return [(tarifs.get("prix_reference", {}), "elec_eur_kwh")]
    if code == "DEFAULT_PRICE_GAZ":
        return [(tarifs.get("prix_reference", {}), "gaz_eur_kwh")]

    # CEE : hors YAML pour l'instant (hypothèses à versionner ultérieurement)
    return []


def _select_best_candidate(candidates: list[tuple[dict, str]], at: date) -> Optional[tuple[dict, str]]:
    """
    Sélectionne le candidat applicable à `at` :
    1. Filtrer ceux dont [valid_from, valid_to] contient `at`.
    2. Parmi ceux-là, garder celui dont valid_from est le plus récent.
    3. Si aucun ne couvre `at`, tomber sur celui dont valid_from est le plus
       récent passé (meilleur effort — on log un warning).
    """
    scored: list[tuple[date, dict, str]] = []
    for entry, key in candidates:
        if not entry or key not in entry:
            continue
        vfrom = _coerce_date(entry.get("valid_from"))
        vto = _coerce_date(entry.get("valid_to"))
        if vfrom and _period_contains(vfrom, vto, at):
            scored.append((vfrom, entry, key))

    if scored:
        scored.sort(key=lambda t: t[0], reverse=True)
        return scored[0][1], scored[0][2]

    # Aucun ne couvre la date → on tombe sur le plus récent dont valid_from ≤ at
    fallback: list[tuple[date, dict, str]] = []
    for entry, key in candidates:
        if not entry or key not in entry:
            continue
        vfrom = _coerce_date(entry.get("valid_from"))
        if vfrom and vfrom <= at:
            fallback.append((vfrom, entry, key))
    if fallback:
        fallback.sort(key=lambda t: t[0], reverse=True)
        logger.warning(
            "ParameterStore: aucune période exacte pour at=%s, fallback sur valid_from=%s",
            at,
            fallback[0][0],
        )
        return fallback[0][1], fallback[0][2]

    # Dernier recours : n'importe quel candidat sans date (entrée "courante")
    for entry, key in candidates:
        if entry and key in entry and entry.get("valid_from") is None:
            return entry, key

    return None


class ParameterStore:
    """
    Façade unique pour tous les paramètres réglementés.

    Usage :
        store = ParameterStore(db=session)
        res = store.get("ACCISE_ELEC", at_date=date(2025, 7, 1), scope={})
        print(res.value, res.source, res.source_ref)
    """

    def __init__(self, db=None):
        self.db = db

    # ── Interface publique ───────────────────────────────────────────
    def get(
        self,
        code: str,
        at_date: Optional[date] = None,
        scope: Optional[dict[str, str]] = None,
    ) -> ParameterResolution:
        """
        Résout un paramètre : DB → YAML → missing.
        Retourne toujours une ParameterResolution (jamais None).
        Pour une valeur manquante, source="missing" et value=0.0.
        """
        if code not in KNOWN_CODES:
            logger.warning("ParameterStore: code inconnu '%s'", code)

        if at_date is None:
            at_date = date.today()
        if isinstance(at_date, datetime):
            at_date = at_date.date()
        scope = scope or {}

        db_res = self._resolve_from_db(code, at_date, scope)
        if db_res is not None:
            return db_res

        yaml_res = self._resolve_from_yaml(code, at_date, scope)
        if yaml_res is not None:
            return yaml_res

        # Trace explicite du trou, pas de hardcode silencieux
        logger.warning(
            "ParameterStore: aucune valeur pour code=%s at=%s scope=%s",
            code,
            at_date,
            scope,
        )
        return ParameterResolution(
            code=code,
            value=0.0,
            source="missing",
            source_ref=None,
            valid_from=None,
            valid_to=None,
            scope=scope,
        )

    def get_value(
        self,
        code: str,
        at_date: Optional[date] = None,
        scope: Optional[dict[str, str]] = None,
        default: float = 0.0,
    ) -> float:
        """Raccourci qui retourne uniquement la valeur (ou `default` si missing)."""
        res = self.get(code, at_date, scope)
        if res.source == "missing":
            return default
        return res.value

    # ── Implémentation : DB ──────────────────────────────────────────
    def _resolve_from_db(self, code: str, at_date: date, scope: dict[str, str]) -> Optional[ParameterResolution]:
        """Tentative de résolution depuis regulated_tariffs (best-effort)."""
        if self.db is None:
            return None
        try:
            from models.market_models import TariffType, TariffComponent
            from services.market_tariff_loader import get_current_tariff
        except Exception:
            return None

        mapping = _DB_CODE_MAP.get(code)
        if mapping is None:
            return None

        try:
            # Conversion date → datetime aware pour compat get_current_tariff
            from datetime import timezone

            at_dt = datetime(at_date.year, at_date.month, at_date.day, tzinfo=timezone.utc)
            tt = TariffType(mapping[0])
            tc = TariffComponent(mapping[1])
            tariff = get_current_tariff(self.db, tt, tc, at_dt)
            if tariff is None:
                return None

            # Conversion unité → EUR/kWh ou ratio
            value = tariff.value
            unit = getattr(tariff, "unit", None)
            unit_str = unit.value if hasattr(unit, "value") else str(unit or "")
            if unit_str in ("EUR_MWH", "EUR/MWh") and code.startswith(("TURPE_ENERGIE", "ACCISE")):
                value = tariff.value / 1000.0
            elif unit_str == "PCT":
                value = tariff.value / 100.0

            valid_from = _coerce_date(getattr(tariff, "valid_from", None))
            valid_to = _coerce_date(getattr(tariff, "valid_to", None))

            return ParameterResolution(
                code=code,
                value=value,
                source="db",
                source_ref=getattr(tariff, "source_ref", None) or mapping[1],
                valid_from=valid_from,
                valid_to=valid_to,
                scope=scope,
            )
        except Exception as exc:
            logger.debug("ParameterStore DB lookup failed for %s: %s", code, exc)
            return None

    # ── Implémentation : YAML ────────────────────────────────────────
    def _resolve_from_yaml(self, code: str, at_date: date, scope: dict[str, str]) -> Optional[ParameterResolution]:
        tarifs = _load_yaml()
        if not tarifs:
            return None
        candidates = _yaml_candidates(code, tarifs)
        if not candidates:
            return None
        selected = _select_best_candidate(candidates, at_date)
        if selected is None:
            return None
        entry, key = selected
        value = entry.get(key)
        if value is None:
            return None
        return ParameterResolution(
            code=code,
            value=float(value),
            source="yaml",
            source_ref=entry.get("source"),
            valid_from=_coerce_date(entry.get("valid_from")),
            valid_to=_coerce_date(entry.get("valid_to")),
            scope=scope,
        )


# ── Mapping code → (TariffType, TariffComponent) pour la DB ─────────────
# Limité aux codes qu'on sait résoudre aujourd'hui. Les autres passent direct
# au YAML.
_DB_CODE_MAP: dict[str, tuple[str, str]] = {
    "TURPE_ENERGIE_C5_BT": ("TURPE", "TURPE_SOUTIRAGE_HPB"),
    "TURPE_ENERGIE_C4_BT": ("TURPE", "TURPE_SOUTIRAGE_HPB"),
    "TURPE_ENERGIE_C3_HTA": ("TURPE", "TURPE_SOUTIRAGE_HPB"),
    "ACCISE_ELEC": ("CSPE", "CSPE_C4"),
    "TVA_NORMALE": ("TVA", "TVA_NORMAL"),
    "TVA_REDUITE": ("TVA", "TVA_REDUIT"),
}


# ── Singleton par défaut (mode "pas de DB") ───────────────────────────────
_default_store: Optional[ParameterStore] = None


def default_store() -> ParameterStore:
    """ParameterStore partagé sans DB (résolution YAML-only)."""
    global _default_store
    if _default_store is None:
        _default_store = ParameterStore(db=None)
    return _default_store
