"""
PROMEOS RegOps - Regle CEE P6 (hints mapping) + moteur calcul kWhc cumac
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

from ..schemas import Finding

# ── Catalogue P6 (chargé une seule fois) ──────────────────────────────────────

_CATALOG_PATH = Path(__file__).resolve().parent.parent / "config" / "cee_p6_catalog.yaml"
_catalog_cache: Optional[dict] = None


def _load_catalog() -> dict:
    global _catalog_cache
    if _catalog_cache is None:
        with open(_CATALOG_PATH, encoding="utf-8") as f:
            _catalog_cache = yaml.safe_load(f)
    return _catalog_cache


def get_fiche(fiche_ref: str) -> Optional[dict]:
    """Return fiche data for a given CEE fiche reference code."""
    catalog = _load_catalog()
    return catalog.get(fiche_ref)


def get_zone_coefficient(zone: str) -> float:
    """Return the zone climatique coefficient. Defaults to 1.0 for unknown zones."""
    catalog = _load_catalog()
    coeffs = catalog.get("zone_climatique_coefficients", {})
    return coeffs.get(zone, 1.0)


def resolve_zone_from_code_postal(code_postal: Optional[str]) -> Optional[str]:
    """Derive zone climatique from a French postal code (2-digit department prefix)."""
    if not code_postal or len(code_postal) < 2:
        return None
    catalog = _load_catalog()
    dept_map = catalog.get("departement_zone_map", {})
    dept = code_postal[:2]
    # Corse: 20 → try 2A/2B; simplified: map both to H3 via "20"
    return dept_map.get(dept)


# ── Calcul kWhc cumac ─────────────────────────────────────────────────────────


@dataclass
class CeeCalculResult:
    """Result of a kWhc cumac computation."""

    fiche_ref: str
    fiche_label: str
    surface_m2: float
    zone_climatique: str
    zone_coefficient: float
    typical_savings_kwh_m2: float
    duree_vie_ans: int
    kwh_cumac: float
    amount_eur: float  # kwh_cumac * CEE_PRIX_MWHC_CUMAC_EUR / 1000


def compute_cee_kwh_cumac(
    fiche_ref: str,
    surface_m2: float,
    zone_climatique: Optional[str] = None,
    code_postal: Optional[str] = None,
    prix_mwhc_cumac_eur: float = 8.50,
) -> CeeCalculResult:
    """
    Calcule les kWhc cumac pour une fiche CEE donnée.

    Formule:
        kWhc cumac = typical_savings_kwh_m2 × surface_m2 × zone_coefficient × duree_vie_ans

    Args:
        fiche_ref: code fiche CEE (ex: BAT-EN-101)
        surface_m2: surface traitée en m²
        zone_climatique: zone climatique (H1a..H3), optionnel si code_postal fourni
        code_postal: code postal du site (pour résolution automatique de la zone)
        prix_mwhc_cumac_eur: prix du MWhc cumac en EUR (default 8.50)

    Returns:
        CeeCalculResult avec le volume kWhc cumac et le montant EUR estimé.

    Raises:
        ValueError: si la fiche est inconnue ou si les données sont insuffisantes.
    """
    fiche = get_fiche(fiche_ref)
    if not fiche:
        raise ValueError(f"Fiche CEE inconnue: {fiche_ref}")

    typical_savings = fiche.get("typical_savings_kwh_m2")
    if typical_savings is None:
        raise ValueError(
            f"Fiche {fiche_ref} n'a pas de typical_savings_kwh_m2 (type services avec savings_pct uniquement)"
        )

    duree_vie = fiche.get("duree_vie_ans")
    if not duree_vie:
        raise ValueError(f"Fiche {fiche_ref} n'a pas de duree_vie_ans")

    if surface_m2 <= 0:
        raise ValueError(f"Surface invalide: {surface_m2}")

    # Resolve zone climatique
    zone = zone_climatique
    if not zone and code_postal:
        zone = resolve_zone_from_code_postal(code_postal)
    if not zone:
        zone = "H2b"  # Fallback: zone tempérée France moyenne

    zone_coeff = get_zone_coefficient(zone)

    kwh_cumac = typical_savings * surface_m2 * zone_coeff * duree_vie
    amount_eur = kwh_cumac * prix_mwhc_cumac_eur / 1000  # MWhc conversion

    return CeeCalculResult(
        fiche_ref=fiche_ref,
        fiche_label=fiche.get("label", ""),
        surface_m2=surface_m2,
        zone_climatique=zone,
        zone_coefficient=zone_coeff,
        typical_savings_kwh_m2=typical_savings,
        duree_vie_ans=duree_vie,
        kwh_cumac=round(kwh_cumac, 2),
        amount_eur=round(amount_eur, 2),
    )


# ── Evaluate (hints, inchangé) ────────────────────────────────────────────────


def evaluate(site, batiments: list, evidences: list, config: dict) -> list[Finding]:
    """
    CEE P6: Pas de reglementation stricte, juste des hints/opportunites.
    Retourne une liste vide ou des suggestions basees sur le profil du site.
    """
    findings = []

    # Example: si surface > 5000m2 et pas de GTB => opportunity CEE BAT-TH-158
    cvc_powers = [b.cvc_power_kw for b in batiments if b.cvc_power_kw]
    if cvc_powers and max(cvc_powers) > 100 and site.surface_m2 and site.surface_m2 > 5000:
        bacs_attestations = [e for e in evidences if e.type and "ATTESTATION_BACS" in str(e.type)]
        if not bacs_attestations:
            findings.append(
                Finding(
                    regulation="CEE_P6",
                    rule_id="CEE_OPPORTUNITY_GTB",
                    status="COMPLIANT",  # Not a compliance issue
                    severity="LOW",
                    confidence="MEDIUM",
                    legal_deadline=None,
                    trigger_condition="Large site without GTB",
                    config_params_used={},
                    inputs_used=["surface_m2", "cvc_power_kw"],
                    missing_inputs=[],
                    explanation="Opportunite CEE BAT-TH-158 (systeme GTB): economies estimees 35 kWh/m2/an.",
                    category="incentive",
                )
            )

    return findings
