"""
PROMEOS — Service orchestration Coût & Contrat (Sprint P1.S2c).

Compose les SoT existants pour relier consommation réelle d'un site à
son contrat énergie, ses composantes de prix et les scénarios
contractuels alternatifs.

Doctrine produit :
- Aucune économie présentée comme certaine. Tout scénario porte une
  mention `Simulation indicative` explicite (cf. EnergyContractRecommendation).
- Toute hypothèse de prix est documentée (`provenance.assumptions`).
- Valeur seed/mock marquée explicitement dans `provenance.source`.

SoT composés :
- cdc_contract_simulator.simulate_contract_strategies — 4 stratégies
  (Fixe 12m / Indexé Spot / Mixte / THS) à partir de la CDC réelle.
- ContratCadre v2 — contrat actif du site (org-scoped).
- price_decomposition_service — décomposition prix (fourniture / TURPE /
  taxes / capacité).
- consumption_unified_service — total kWh sur période.
- cost_by_period_service — coût total estimé.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from schemas.energy_orchestration import (
    EnergyContractRecommendation,
    EnergyContractScenario,
    EnergyContractSummary,
    EnergyCostAssumptions,
    EnergyCostContractKpis,
    EnergyCostContractResponse,
    EnergyKpi,
    EnergyPeriod,
    EnergyPriceComponent,
    EnergyProvenance,
    EnergyScope,
)
from services.energy_orchestration.synthesis import _build_provenance, resolve_period


TZ_PARIS = ZoneInfo("Europe/Paris")


# Mapping scénarios par défaut — clés stables exposées au FE.
DEFAULT_SCENARIOS = ("fixed", "indexed", "mixed", "ths")

_SCENARIO_LABEL = {
    "fixed": "Fixe 12 mois",
    "indexed": "Indexé EPEX Spot",
    "mixed": "Mixte baseload / pointe",
    "ths": "THS — Tarif Heures Solaires",
}

_RISK_BY_NAME = {
    "faible": "faible",
    "modéré": "modéré",
    "modere": "modéré",
    "élevé": "élevé",
    "eleve": "élevé",
}


class CostVsContractError(Exception):
    """Erreur fonctionnelle cost-vs-contract (mappée HTTP 400/404)."""

    def __init__(self, message: str, hint: Optional[str] = None, *, http_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint
        self.http_code = http_code


# ── Helpers ────────────────────────────────────────────────────────────


def _provenance(service: str, formula: str, period: EnergyPeriod, **extra) -> EnergyProvenance:
    return _build_provenance(service=service, formula=formula, period=period, **extra)


def _kpi(
    key: str,
    label: str,
    value,
    unit: str,
    scope: EnergyScope,
    period: EnergyPeriod,
    *,
    formula: str,
    confidence: float = 0.8,
    assumptions: Optional[list[str]] = None,
    state: Optional[str] = None,
) -> EnergyKpi:
    if value is None:
        kpi_state = "inactif"
    else:
        kpi_state = state or "sain"
    return EnergyKpi(
        key=key,
        label=label,
        value=value,
        unit=unit,  # type: ignore[arg-type]
        state=kpi_state,  # type: ignore[arg-type]
        period=period,
        scope=scope,
        provenance=_provenance(
            service=f"energy_orchestration.cost_vs_contract._kpi ({key})",
            formula=formula,
            period=period,
            confidence=confidence if value is not None else 0.0,
            assumptions=assumptions or [],
        ),
    )


# ── Contrat actif ──────────────────────────────────────────────────────


def _resolve_active_contract(db: Session, scope: EnergyScope, period: EnergyPeriod) -> Optional[EnergyContractSummary]:
    """Cherche le contrat ContratCadre actif sur la période pour le site."""
    if scope.kind != "site" or scope.id is None:
        return None

    try:
        from models.contract_v2_models import ContratCadre

        # Stratégie MVP : on prend le contrat le plus récent dont la
        # période [date_debut, date_fin] couvre period.end.
        ref_date = period.end.date() if hasattr(period.end, "date") else period.end
        q = db.query(ContratCadre).filter(
            ContratCadre.date_debut <= ref_date,
            ContratCadre.date_fin >= ref_date,
        )
        # org-scoping si dispo
        if scope.org_id is not None:
            q = q.filter(ContratCadre.org_id == scope.org_id)
        contract = q.order_by(ContratCadre.date_debut.desc()).first()
        if contract is None:
            return None

        # Mapping type contrat → ContractType normalisé.
        raw_type = (getattr(contract, "type_contrat", None) or "").lower()
        if "fixe" in raw_type or "fixed" in raw_type:
            contract_type = "fixed"
        elif "index" in raw_type or "spot" in raw_type:
            contract_type = "indexed"
        elif "mixte" in raw_type or "mixed" in raw_type:
            contract_type = "mixed"
        elif "ths" in raw_type or "solaire" in raw_type:
            contract_type = "ths"
        else:
            contract_type = "unknown"

        return EnergyContractSummary(
            contract_id=str(contract.id),
            supplier_name=getattr(contract, "fournisseur", None),
            contract_type=contract_type,  # type: ignore[arg-type]
            start_date=contract.date_debut.isoformat() if contract.date_debut else None,
            end_date=contract.date_fin.isoformat() if contract.date_fin else None,
            subscribed_power_kva=getattr(contract, "puissance_souscrite_kva", None),
            provenance=_provenance(
                service="ContratCadre v2",
                formula="ContratCadre WHERE date_debut <= ref_date <= date_fin",
                period=period,
                confidence=0.95,
                assumptions=[
                    "ref_date = period.end",
                    "contrat le plus récent en cas de chevauchement",
                ],
            ),
        )
    except Exception:
        return None


# ── Total consommation + coût ──────────────────────────────────────────


def _resolve_consumption_total(db: Session, scope: EnergyScope, period: EnergyPeriod) -> tuple[Optional[float], float]:
    """Retourne (total_kwh, confidence ∈ [0,1])."""
    if scope.kind != "site" or scope.id is None:
        return None, 0.0
    try:
        from models.enums import EnergyVector
        from services.consumption_unified_service import get_consumption_summary

        summary = get_consumption_summary(
            db,
            int(scope.id),
            period.start.date(),
            period.end.date(),
            energy_vector=EnergyVector.ELECTRICITY,
        )
        if not summary:
            return None, 0.0
        value = summary.get("value_kwh")
        confidence = {"high": 1.0, "medium": 0.7, "low": 0.4, "none": 0.0}.get(summary.get("confidence", "none"), 0.0)
        return (value if value and value > 0 else None), confidence
    except Exception:
        return None, 0.0


def _resolve_total_cost(db: Session, scope: EnergyScope, period: EnergyPeriod) -> tuple[Optional[float], float, dict]:
    """Retourne (total_cost_eur, confidence, raw_summary_dict)."""
    if scope.kind != "site" or scope.id is None:
        return None, 0.0, {}
    try:
        from services.cost_by_period_service import get_cost_by_period

        months = max(1, period.days // 30)
        data = get_cost_by_period(db, int(scope.id), months=months)
        total = (data or {}).get("total_eur")
        return (total if total and total > 0 else None), 0.8, data or {}
    except Exception:
        return None, 0.0, {}


# ── Décomposition prix ────────────────────────────────────────────────


def _build_price_decomposition(
    db: Session,
    scope: EnergyScope,
    period: EnergyPeriod,
    total_kwh: Optional[float],
    assumptions: EnergyCostAssumptions,
) -> tuple[list[EnergyPriceComponent], Optional[float], Optional[float], Optional[float], dict]:
    """Décompose le prix moyen via PriceDecompositionService.

    Returns:
        (components, supply_cost_eur, network_cost_eur, taxes_cost_eur, dec_dict)
    """
    components: list[EnergyPriceComponent] = []
    supply_eur: Optional[float] = None
    network_eur: Optional[float] = None
    taxes_eur: Optional[float] = None
    dec_dict: dict = {}

    if not total_kwh or total_kwh <= 0:
        return components, supply_eur, network_eur, taxes_eur, dec_dict

    try:
        from services.price_decomposition_service import PriceDecompositionService

        svc = PriceDecompositionService(db)
        # MVP : on appelle compute() sur profil par défaut "BT" si la
        # signature l'autorise. La structure réelle de l'API peut varier
        # selon version — on tente plusieurs signatures défensivement.
        result = None
        for sig in (
            lambda: svc.compute(period_start=period.start, period_end=period.end),
            lambda: svc.compute(period.start, period.end),
            lambda: svc.compute(),
        ):
            try:
                result = sig()
                if result is not None:
                    break
            except TypeError:
                continue
            except Exception:
                continue
        if result is None:
            return components, supply_eur, network_eur, taxes_eur, dec_dict

        if hasattr(result, "to_dict"):
            dec_dict = result.to_dict()
        elif isinstance(result, dict):
            dec_dict = result
        else:
            dec_dict = {}

        volume_mwh = total_kwh / 1000.0
        energy = dec_dict.get("energy_eur_mwh") or 0.0
        turpe = dec_dict.get("turpe_eur_mwh") or 0.0
        cspe = dec_dict.get("cspe_eur_mwh") or 0.0
        capacity = dec_dict.get("capacity_eur_mwh") or 0.0
        cta = dec_dict.get("cta_eur_mwh") or 0.0
        cee = dec_dict.get("cee_eur_mwh") or 0.0
        total_ht = dec_dict.get("total_ht_eur_mwh") or (energy + turpe + cspe + capacity + cta + cee)

        supply_eur = round(energy * volume_mwh, 2)
        network_eur = round(turpe * volume_mwh, 2)
        taxes_eur = round((cspe + cta + cee) * volume_mwh, 2)
        capacity_eur = round(capacity * volume_mwh, 2)

        total_components_eur = supply_eur + network_eur + taxes_eur + capacity_eur

        def _share(amount: float) -> Optional[float]:
            if total_components_eur <= 0:
                return None
            return round(amount / total_components_eur * 100, 1)

        if assumptions:
            assumptions.turpe_version = dec_dict.get("tariff_version") or assumptions.turpe_version
            assumptions.spot_price_source = dec_dict.get("calculation_method") or assumptions.spot_price_source

        def _component(key: str, label: str, amount: float, price_eur_mwh: float) -> EnergyPriceComponent:
            return EnergyPriceComponent(
                key=key,  # type: ignore[arg-type]
                label=label,
                amount_eur=amount,
                price_eur_mwh=round(price_eur_mwh, 2),
                share_pct=_share(amount),
                provenance=_provenance(
                    service="price_decomposition_service.PriceDecompositionService",
                    formula=f"{key}_eur_mwh × volume_mwh",
                    period=period,
                    confidence=0.8,
                    assumptions=[
                        f"volume_mwh={volume_mwh:.1f}",
                        f"tariff_version={dec_dict.get('tariff_version') or 'inconnu'}",
                    ],
                ),
            )

        components = [
            _component("supply", "Fourniture", supply_eur, energy),
            _component("network", "Acheminement TURPE", network_eur, turpe),
            _component("taxes", "Taxes (CSPE + CTA + CEE)", taxes_eur, cspe + cta + cee),
        ]
        if capacity_eur > 0:
            components.append(_component("capacity", "Capacité", capacity_eur, capacity))
    except Exception:
        # Décomposition non disponible : on retourne liste vide + flags
        # explicites dans les assumptions.
        if assumptions:
            assumptions.notes.append("Décomposition prix indisponible — composantes non calculées.")
        return components, supply_eur, network_eur, taxes_eur, dec_dict

    return components, supply_eur, network_eur, taxes_eur, dec_dict


# ── Scénarios contractuels ─────────────────────────────────────────────


def _build_scenarios(
    db: Session,
    scope: EnergyScope,
    period: EnergyPeriod,
    requested_keys: list[str],
    total_kwh: Optional[float],
    total_cost_eur: Optional[float],
    active_contract: Optional[EnergyContractSummary],
    assumptions: EnergyCostAssumptions,
) -> tuple[list[EnergyContractScenario], Optional[EnergyContractRecommendation]]:
    """Compose les scénarios via cdc_contract_simulator.

    Le total_cost_eur du contrat actif sert de référence pour
    `delta_vs_current_eur`. Si pas de cost réel, on tombe sur le scénario
    "current" simulé via Fixe 12 mois ou la stratégie matching contract_type.
    """
    if scope.kind != "site" or scope.id is None:
        return [], None

    simulator_payload = None
    try:
        from services.cdc_contract_simulator import simulate_contract_strategies

        simulator_payload = simulate_contract_strategies(db, int(scope.id))
    except Exception:
        simulator_payload = None

    if not simulator_payload or "error" in simulator_payload:
        if assumptions:
            assumptions.notes.append("Données CDC insuffisantes pour simuler les scénarios contractuels.")
        return [], None

    cdc_profile = simulator_payload.get("cdc_profile") or {}
    raw_strategies = simulator_payload.get("strategies") or []
    raw_recommendation = simulator_payload.get("recommendation") or {}

    # Mapping name → key normalisée stable.
    def _normalize_key(name: str) -> str:
        n = (name or "").lower()
        if "fixe" in n or "fixed" in n:
            return "fixed"
        if "index" in n or "spot" in n or "epex" in n:
            return "indexed"
        if "mixte" in n or "mixed" in n:
            return "mixed"
        if "ths" in n or "solaire" in n:
            return "ths"
        return "other"

    # Ref cost = total_cost_eur réel, sinon coût Fixe 12 mois.
    fallback_fixed_cost = next(
        (s.get("cost_eur_year") for s in raw_strategies if _normalize_key(s.get("name", "")) == "fixed"),
        None,
    )
    ref_cost = total_cost_eur if total_cost_eur is not None else fallback_fixed_cost

    scenarios: list[EnergyContractScenario] = []
    for raw in raw_strategies:
        key = _normalize_key(raw.get("name", ""))
        if key == "other":
            continue
        if requested_keys and key not in requested_keys:
            continue

        est_cost = raw.get("cost_eur_year")
        weighted = raw.get("price_avg_eur_kwh")
        weighted_eur_mwh = round(weighted * 1000, 2) if isinstance(weighted, (int, float)) else None
        risk = _RISK_BY_NAME.get((raw.get("risk_level") or "").lower(), "modéré")
        is_current = active_contract is not None and active_contract.contract_type == key
        delta = None
        if isinstance(est_cost, (int, float)) and isinstance(ref_cost, (int, float)):
            delta = round(est_cost - ref_cost, 2)

        scen_assumptions = [
            f"profil CDC : {cdc_profile.get('type', 'inconnu')}",
            f"baseload_ratio={cdc_profile.get('baseload_ratio')}",
            f"hp_ratio={cdc_profile.get('hp_ratio')}",
        ]
        if key == "indexed":
            scen_assumptions.append(
                "Sensibilité saisonnière : cost_low = 0.78× ; cost_high = 1.45× (référence EPEX 2024-2025)"
            )
        if key == "ths":
            scen_assumptions.append("Tranches solaires (avr-sep 10h-15h ; oct-mar 11h-14h)")

        scenarios.append(
            EnergyContractScenario(
                key=f"{key}_default",
                label=_SCENARIO_LABEL.get(key, raw.get("name", "")),
                estimated_cost_eur=est_cost,
                weighted_price_eur_mwh=weighted_eur_mwh,
                risk_level=risk,  # type: ignore[arg-type]
                status="current" if is_current else "simulation",
                delta_vs_current_eur=delta,
                provenance=_provenance(
                    service="cdc_contract_simulator.simulate_contract_strategies",
                    formula="Σ kWh × prix_scénario sur CDC 12 mois (cf. _build_hourly_profile)",
                    period=period,
                    confidence=0.6,
                    assumptions=scen_assumptions,
                ),
                assumptions=scen_assumptions,
            )
        )

    # Recommandation : prendre la reco du simulator si dispo et la mapper.
    if raw_recommendation:
        rec_name = raw_recommendation.get("strategy") or ""
        rec_key = f"{_normalize_key(rec_name)}_default"
        rec_message = raw_recommendation.get("reasoning") or ("Scénario recommandé selon le profil CDC du site.")
        recommendation = EnergyContractRecommendation(
            recommended_scenario=rec_key if any(s.key == rec_key for s in scenarios) else None,
            message=rec_message,
            confidence=0.6,
            provenance=_provenance(
                service="cdc_contract_simulator._recommend_strategy",
                formula="règle métier sur profil CDC + risk_level scénario",
                period=period,
                confidence=0.6,
                assumptions=[
                    "Doctrine : aucune économie présentée comme certaine",
                    "Reco indicative — à valider avec acheteur énergie",
                ],
            ),
        )
    else:
        recommendation = None

    if simulator_payload and assumptions:
        assumptions.notes.append(f"Profil CDC détecté : {cdc_profile.get('type', 'inconnu')}")

    return scenarios, recommendation


# ── Orchestration principale ───────────────────────────────────────────


def build_cost_vs_contract(
    db: Session,
    *,
    scope_kind: str,
    scope_id: Optional[int],
    org_id: Optional[int],
    period_label: str = "12m",
    scenarios: Optional[list[str]] = None,
    now: Optional[datetime] = None,
) -> EnergyCostContractResponse:
    """Compose la vue Coût & contrat.

    Args:
        scope_kind : 'site' ou 'meter' (org/portfolio non supportés MVP).
        scope_id : id du site / compteur.
        org_id : id organisation pour scope_utils.
        period_label : ex '7d' | '30d' | '90d' | '12m' | 'ytd'.
        scenarios : sous-ensemble parmi {fixed, indexed, mixed, ths}.
                    Par défaut : tous (DEFAULT_SCENARIOS).
        now : reproductibilité tests.

    Raises:
        CostVsContractError : scope invalide (router → HTTP 400/404).
    """
    if scope_kind not in ("site", "meter"):
        raise CostVsContractError(
            f"scope_kind '{scope_kind}' non supporté pour cost-vs-contract",
            hint="utiliser scope='site' ou scope='meter' (org/portfolio à venir)",
        )
    if scope_id is None:
        raise CostVsContractError(
            "scope_id obligatoire pour cost-vs-contract",
            hint=f"fournir scope_id={scope_kind}_id pour cibler le profil",
        )

    requested_scenarios = list(scenarios) if scenarios else list(DEFAULT_SCENARIOS)
    invalid = [s for s in requested_scenarios if s not in DEFAULT_SCENARIOS]
    if invalid:
        raise CostVsContractError(
            f"scénarios invalides : {invalid}",
            hint=f"valeurs autorisées : {list(DEFAULT_SCENARIOS)}",
        )

    period = resolve_period(period_label, now=now)
    scope = EnergyScope(
        kind=scope_kind,  # type: ignore[arg-type]
        id=scope_id,
        org_id=org_id,
    )
    assumptions = EnergyCostAssumptions(
        spot_price_source="EPEX SPOT FR (source: cdc_contract_simulator constants)",
        spot_year_reference=2024,
        turpe_version=None,
        fallback_price_used=False,
        notes=[
            "Doctrine PROMEOS : toute simulation contractuelle est indicative",
            "Prix mensuels saisonniers issus de SPOT_MONTHLY_RATIO (constants module)",
        ],
    )

    # 1. Contrat actif
    active_contract = _resolve_active_contract(db, scope, period)

    # 2. Total kWh + total coût
    total_kwh, kwh_conf = _resolve_consumption_total(db, scope, period)
    total_cost_eur, cost_conf, _cost_dict = _resolve_total_cost(db, scope, period)

    # 3. Prix pondéré
    if total_kwh and total_cost_eur and total_kwh > 0:
        weighted_price = round(total_cost_eur / total_kwh * 1000.0, 1)
    else:
        weighted_price = None

    # 4. Décomposition prix
    components, supply_eur, network_eur, taxes_eur, _dec_dict = _build_price_decomposition(
        db, scope, period, total_kwh, assumptions
    )

    # 5. KPI strip
    kpis = EnergyCostContractKpis(
        total_cost_eur=_kpi(
            "total_cost_eur",
            "Coût estimé",
            total_cost_eur,
            "€",
            scope,
            period,
            formula="cost_by_period_service.get_cost_by_period.total_eur",
            confidence=cost_conf,
            assumptions=[
                "DEFAULT_PRICE_ELEC_EUR_KWH si pas de contrat actif",
                "TURPE inclus si TariffCalendar attaché site",
            ],
        ),
        consumption_kwh=_kpi(
            "consumption_kwh",
            "Consommation",
            total_kwh,
            "kWh",
            scope,
            period,
            formula="consumption_unified_service.get_consumption_summary.value_kwh",
            confidence=kwh_conf,
            assumptions=[
                "seuil 80 % couverture metered (sinon billed)",
                "energy_vector=ELECTRICITY",
            ],
        ),
        weighted_price_eur_mwh=_kpi(
            "weighted_price_eur_mwh",
            "Prix moyen pondéré",
            weighted_price,
            "€/MWh",
            scope,
            period,
            formula="total_cost_eur / total_kwh × 1000",
            confidence=min(kwh_conf, cost_conf),
            assumptions=[
                "valeur null si total_kwh = 0 (pas de division par zéro)",
            ],
        ),
        supply_cost_eur=_kpi(
            "supply_cost_eur",
            "Coût fourniture",
            supply_eur,
            "€",
            scope,
            period,
            formula="energy_eur_mwh × volume_mwh (price_decomposition_service)",
        ),
        network_cost_eur=_kpi(
            "network_cost_eur",
            "Coût acheminement (TURPE)",
            network_eur,
            "€",
            scope,
            period,
            formula="turpe_eur_mwh × volume_mwh",
            assumptions=[
                f"tariff_version={assumptions.turpe_version or 'inconnu'}",
            ],
        ),
        taxes_cost_eur=_kpi(
            "taxes_cost_eur",
            "Coût taxes (CSPE + CTA + CEE)",
            taxes_eur,
            "€",
            scope,
            period,
            formula="(cspe + cta + cee)_eur_mwh × volume_mwh",
        ),
    )

    # 6. Scénarios + recommandation
    scenario_list, recommendation = _build_scenarios(
        db,
        scope,
        period,
        requested_scenarios,
        total_kwh,
        total_cost_eur,
        active_contract,
        assumptions,
    )

    # 7. Empty state
    warnings: list[str] = []
    empty_state: Optional[str] = None
    if total_kwh is None and not active_contract and not scenario_list:
        empty_state = (
            "Données insuffisantes pour relier consommation et contrat. "
            "Vérifier la connexion compteur et l'import du contrat actif."
        )
        warnings.append("Toutes les composantes (kWh, coût, contrat, scénarios) sont vides.")

    provenance = _provenance(
        service="energy_orchestration.cost_vs_contract.build_cost_vs_contract",
        formula="orchestration KPI + price_decomposition + 4 scénarios CDC simulés",
        period=period,
        confidence=0.7 if scenario_list else 0.3,
        assumptions=[
            "timezone Europe/Paris",
            "all scenarios are simulations — no guaranteed savings",
            "weighted_price_eur_mwh = cost_eur / kwh × 1000 (null si kwh=0)",
        ],
    )

    return EnergyCostContractResponse(
        scope=scope,
        period=period,
        active_contract=active_contract,
        kpis=kpis,
        price_decomposition=components,
        scenarios=scenario_list,
        recommendation=recommendation,
        assumptions=assumptions,
        warnings=warnings,
        empty_state=empty_state,
        provenance=provenance,
    )
