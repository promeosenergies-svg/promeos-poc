"""
PROMEOS — Schemas Pydantic pour Power Intelligence.
"""

from typing import Any, Optional

from pydantic import BaseModel


# === Power Profile ===


class PowerProfileResponse(BaseModel):
    """KPIs puissance : P_max, P_mean, P_base, E_totale, etc."""

    site_id: Optional[int] = None
    site_name: Optional[str] = None
    P_max_kw: Optional[float] = None
    P_mean_kw: Optional[float] = None
    P_base_kw: Optional[float] = None
    E_totale_kwh: Optional[float] = None
    taux_utilisation_ps: Optional[float] = None
    facteur_forme: Optional[float] = None
    tan_phi: Optional[float] = None
    completude_pct: Optional[float] = None

    model_config = {"from_attributes": True}


# === Power Contract ===


class PowerContractDetail(BaseModel):
    """Detail parametres contractuels puissance."""

    fta_code: Optional[str] = None
    domaine_tension: Optional[str] = None
    type_compteur: Optional[str] = None
    ps_par_poste_kva: Optional[dict[str, Any]] = None
    p_raccordement_kva: Optional[float] = None
    p_limite_soutirage_kva: Optional[float] = None
    has_periode_mobile: Optional[bool] = None
    date_debut: Optional[str] = None


class PowerContractResponse(BaseModel):
    """Reponse parametres contractuels de puissance."""

    site_id: int
    contract: Optional[PowerContractDetail] = None


# === Peaks ===


class PowerPeaksResponse(BaseModel):
    """Detection des pics >= seuil_pct% de la PS."""

    site_id: Optional[int] = None
    peaks: Optional[list[dict[str, Any]]] = None
    cmdps: Optional[dict[str, Any]] = None
    seuil_pct: Optional[float] = None
    total_peaks: Optional[int] = None

    model_config = {"from_attributes": True}


# === Power Factor ===


class PowerFactorResponse(BaseModel):
    """Analyse facteur de puissance (tan phi)."""

    site_id: Optional[int] = None
    tan_phi_moyen: Optional[float] = None
    cos_phi_moyen: Optional[float] = None
    seuil_turpe: Optional[float] = 0.4
    conforme: Optional[bool] = None
    depassements: Optional[list[dict[str, Any]]] = None
    penalite_estimee_eur: Optional[float] = None

    model_config = {"from_attributes": True}


# === Optimize PS ===


class OptimizePsResponse(BaseModel):
    """Resultat optimisation puissance souscrite."""

    site_id: Optional[int] = None
    current: Optional[dict[str, Any]] = None
    recommended: Optional[dict[str, Any]] = None
    savings_eur_an: Optional[float] = None
    methodology: Optional[str] = None

    model_config = {"from_attributes": True}


# === NEBCO ===


class NebcoResponse(BaseModel):
    """Eligibilite NEBCO pour un site."""

    site_id: Optional[int] = None
    eligible_technique: Optional[bool] = None
    P_max_kw: Optional[float] = None
    checklist: Optional[list[dict[str, Any]]] = None
    potentiel: Optional[dict[str, Any]] = None
    justification: Optional[str] = None

    model_config = {"from_attributes": True}


# === NEBCO Portfolio ===


class NebcoSiteDetail(BaseModel):
    """Detail NEBCO pour un site dans le portefeuille."""

    site_id: int
    site_name: Optional[str] = None
    eligible_technique: Optional[bool] = None
    P_max_kw: Optional[float] = None
    P_effacable_kw: Optional[float] = None
    revenu_central_eur_an: Optional[float] = None
    justification: Optional[str] = None


class NebcoAgregation(BaseModel):
    """Agregation NEBCO portefeuille."""

    P_effacable_totale_kw: Optional[float] = None
    revenu_central_eur_an: Optional[float] = None
    revenu_min_eur_an: Optional[float] = None
    revenu_max_eur_an: Optional[float] = None
    formule: Optional[str] = None


class NebcoParametrageTarif(BaseModel):
    """Parametrage tarif NEBCO."""

    tarif_central_eur_kw_an: float
    tarif_min_eur_kw_an: float
    tarif_max_eur_kw_an: float


class NebcoPortfolioResponse(BaseModel):
    """Agregation NEBCO sur tous les sites."""

    n_sites_evalues: int
    n_sites_eligibles: int
    parametrage_tarif: NebcoParametrageTarif
    agregation: NebcoAgregation
    sites: list[NebcoSiteDetail]
    source: Optional[str] = None
    computed_at: Optional[str] = None
