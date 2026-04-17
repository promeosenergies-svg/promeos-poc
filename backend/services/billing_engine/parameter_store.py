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
- Unités par famille de code (non homogènes — voir KNOWN_CODES et
  `_resolve_from_db` pour les conversions EUR_MWH → EUR/kWh) :
    * TURPE_ENERGIE_*, ACCISE_*, ATRD_GAZ (flat legacy) : EUR/kWh
    * TURPE_GESTION_*                                   : EUR/mois
    * ATRD_GAZ_*_ABO                                    : EUR/an
    * ATRD_GAZ_*_PROP                                   : EUR/MWh
    * ATRD_GAZ_*_CAPA, ATRD_GAZ_T4_CAPA_GTE500          : EUR/MWh/j/an
    * ATRD_GAZ_TP_DISTANCE                              : EUR/mètre/an
    * CTA_*_RATE, CTA_GAZ_TRANSPORT_COEF, TVA_*         : ratio (ex. 0,208)
  Les briques consommatrices sont responsables de l'homogénéité des calculs.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from utils.parameter_store_base import (
    ParameterResolution,
    coerce_date as _coerce_date,
    load_yaml_section,
    paris_today,
    period_contains as _base_period_contains,
    warn_unknown_once,
)

logger = logging.getLogger(__name__)

# Codes déjà signalés comme inconnus — module-level set isolé du pilotage
# (helper `warn_unknown_once` accepte le set en paramètre pour éviter qu'un
# test pilotage pollue le cache billing — cf. audit Sprint 5b).
_unknown_codes_seen: set[str] = set()

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
        # Acheminement gaz (EUR/kWh flat — fallback legacy)
        "ATRD_GAZ",
        "ATRT_GAZ",
        # ATRD7 détaillé par option (Vague 2)
        # Abonnement annuel par option (EUR/an) — assiette CTA gaz
        "ATRD_GAZ_T1_ABO",
        "ATRD_GAZ_T2_ABO",
        "ATRD_GAZ_T3_ABO",
        "ATRD_GAZ_T4_ABO",
        "ATRD_GAZ_TP_ABO",
        # Terme proportionnel par option (EUR/MWh)
        "ATRD_GAZ_T1_PROP",
        "ATRD_GAZ_T2_PROP",
        "ATRD_GAZ_T3_PROP",
        "ATRD_GAZ_T4_PROP",
        "ATRD_GAZ_TP_PROP",
        # Terme capacité journalière (EUR/MWh/j/an) — T4 et TP uniquement
        # T4 a une grille marginale : _CAPA = tranche CJA<500, _CAPA_GTE500 = tranche CJA≥500
        "ATRD_GAZ_T4_CAPA",
        "ATRD_GAZ_T4_CAPA_GTE500",
        "ATRD_GAZ_TP_CAPA",
        "ATRD_GAZ_TP_DISTANCE",  # EUR/mètre/an — TP uniquement
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
        # Coefficient de proportionnalité CTA gaz (part transport imputée aux
        # clients distribution, révisé chaque 1/07 par arrêté annuel).
        "CTA_GAZ_TRANSPORT_COEF",
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


# `ParameterResolution` et `_coerce_date` proviennent désormais de
# `utils.parameter_store_base` (Sprint 5b dedup). Rétro-compat totale :
# importée sous le nom `ParameterResolution` depuis ce module.


# ── YAML loader ────────────────────────────────────────────────────────────
# Cache unique partagé avec `config.tarif_loader.load_tarifs` — même fichier,
# mêmes sémantiques, une seule source de vérité. Évite que `reload_tarifs()`
# côté legacy laisse un ParameterStore stale en tests.


def _load_yaml() -> dict:
    """Charge le YAML tarifs complet (dict vide si loader indispo)."""
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


def _period_contains(valid_from: Optional[date], valid_to: Optional[date], at: date) -> bool:
    """True si `at` est dans [valid_from, valid_to] (bornes incluses).

    Wrapper sur `utils.parameter_store_base.period_contains` avec l'ordre
    d'arguments historique billing (valid_from, valid_to, at) pour éviter
    de toucher les ~50 call sites internes.
    """
    return _base_period_contains(at, valid_from, valid_to)


def _turpe_candidates(tarifs: dict, seg: str, value_key: str) -> list[tuple[dict, str]]:
    """Collecte les candidats TURPE 6 et TURPE 7 pour un segment/terme donné."""
    out: list[tuple[dict, str]] = []
    for root_key in ("turpe_6", "turpe"):
        root = tarifs.get(root_key)
        if root and "segments" in root and seg in root["segments"]:
            entry = dict(root["segments"][seg])
            entry["valid_from"] = root.get("valid_from")
            entry["valid_to"] = root.get("valid_to")
            entry["source"] = root.get("source")
            out.append((entry, value_key))
    return out


# ── Table de résolution YAML → code ───────────────────────────────────────
# Chaque entrée retourne une liste de candidats (dict YAML) et la clé à lire.
# On parcourt les candidats, on garde ceux dont la période contient `at_date`,
# et on retient celui dont `valid_from` est le plus récent (cas d'entrées
# successives type "accise_gaz_2024" / "accise_gaz_2025_jan" / "accise_gaz").
def _yaml_candidates(code: str, tarifs: dict) -> list[tuple[dict, str]]:
    """Retourne une liste (entry_dict, value_key) pour un code donné."""
    # TURPE (gère TURPE 6 et TURPE 7 simultanément)
    if code.startswith("TURPE_ENERGIE_"):
        return _turpe_candidates(tarifs, code.replace("TURPE_ENERGIE_", ""), "energie_eur_kwh")

    if code.startswith("TURPE_GESTION_"):
        return _turpe_candidates(tarifs, code.replace("TURPE_GESTION_", ""), "gestion_eur_mois")

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

    # Acheminement gaz — flat rate legacy
    if code == "ATRD_GAZ":
        return [(tarifs.get("atrd_gaz", {}), "rate_eur_kwh")]
    if code == "ATRT_GAZ":
        # Deux sections chronologiques : atrt_gaz (2025) + atrt_gaz_2026 (+3,41%)
        return [
            (tarifs.get("atrt_gaz", {}), "rate_eur_kwh"),
            (tarifs.get("atrt_gaz_2026", {}), "rate_eur_kwh"),
        ]

    # ATRD7 détaillé par option (Vague 2)
    # Codes : ATRD_GAZ_{T1,T2,T3,T4,TP}_{ABO,PROP,CAPA,CAPA_GTE500,DISTANCE}
    # Deux sections chronologiques dans le YAML : atrd7_gaz_tiers (2024) et
    # atrd7_gaz_tiers_2025 (révision +6,06% au 1/07/2025). _select_best_candidate
    # choisit la bonne selon at_date.
    if code.startswith("ATRD_GAZ_") and code != "ATRD_GAZ":
        # Parse "ATRD_GAZ_T4_CAPA_GTE500" → tier="T4", term="CAPA_GTE500"
        # Parse "ATRD_GAZ_T1_ABO" → tier="T1", term="ABO"
        parts = code.split("_", 3)
        if len(parts) < 4:
            return []
        _, _, tier, term = parts
        term_key_map = {
            "ABO": "abo_eur_an",
            "PROP": "var_eur_mwh",
            "CAPA": "capa_eur_mwh_j_an",
            "CAPA_GTE500": "capa_eur_mwh_j_an_gte_500",
            "DISTANCE": "distance_eur_per_metre_an",
        }
        value_key = term_key_map.get(term)
        if value_key is None:
            return []
        out_atrd7: list[tuple[dict, str]] = []
        for root_key in ("atrd7_gaz_tiers", "atrd7_gaz_tiers_2025"):
            root = tarifs.get(root_key, {})
            tier_entry = dict(root.get("tiers", {}).get(tier, {}))
            if tier_entry and value_key in tier_entry:
                tier_entry["valid_from"] = root.get("valid_from")
                tier_entry["valid_to"] = root.get("valid_to")
                tier_entry["source"] = root.get("source")
                out_atrd7.append((tier_entry, value_key))
        return out_atrd7

    # CTA — ratio (taux_pct / 100), énumère les historiques + courant
    if code in (
        "CTA_ELEC_DIST_RATE",
        "CTA_ELEC_TRANS_RATE",
        "CTA_GAZ_DIST_RATE",
        "CTA_GAZ_TRANS_RATE",
    ):
        cta_subkey = {
            "CTA_ELEC_DIST_RATE": "elec",
            "CTA_ELEC_TRANS_RATE": "elec_transport",
            "CTA_GAZ_DIST_RATE": "gaz",
            "CTA_GAZ_TRANS_RATE": "gaz_transport",
        }[code]
        cta_out: list[tuple[dict, str]] = []
        for root_key in ("cta_2021", "cta"):
            entry = dict(tarifs.get(root_key, {}).get(cta_subkey, {}))
            if "taux_pct" in entry:
                entry["_ratio"] = entry["taux_pct"] / 100.0
                cta_out.append((entry, "_ratio"))
        return cta_out

    # Coefficient CTA gaz transport — révisé chaque 1/07 par arrêté annuel
    if code == "CTA_GAZ_TRANSPORT_COEF":
        out_coef: list[tuple[dict, str]] = []
        cta = tarifs.get("cta", {})
        for subkey in ("gaz_transport_coef", "gaz_transport_coef_2025"):
            entry = dict(cta.get(subkey, {}))
            if "valeur_pct" in entry:
                entry["_ratio"] = entry["valeur_pct"] / 100.0
                out_coef.append((entry, "_ratio"))
        return out_coef

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
            warn_unknown_once(_unknown_codes_seen, logger, code, module_tag="ParameterStore")

        if at_date is None:
            # Sprint 5b fix : Europe/Paris forcé (évite J-1 sous Docker UTC
            # au tournant d'année, cf. fix pilotage Sprint 2 remonté en base).
            at_date = paris_today()
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
