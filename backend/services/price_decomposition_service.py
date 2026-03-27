"""
PROMEOS — Moteur de decomposition prix electricite France.

Assemble les 7 briques reglementaires pour produire un prix complet EUR/MWh :
  1. Energie (commodity spot ou forward)
  2. TURPE (acheminement, moyenne ponderee horosaisonniere)
  3. CSPE / Accise electricite
  4. Capacite (mecanisme encheres)
  5. CEE (Certificats Economies Energie)
  6. CTA (Contribution Tarifaire Acheminement — sur part fixe TURPE)
  7. TVA

REGLE : zero constante hardcodee. Tous les tarifs viennent de regulated_tariffs (DB).
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from models.market_models import (
    PriceDecomposition,
    TariffType,
    TariffComponent,
)
from services.market_tariff_loader import get_current_tariff
from services.market_data_service import MarketDataService

logger = logging.getLogger(__name__)


# -- Profils de charge horosaisonniers (repartition % du volume annuel) ------
# Source : profils types RTE/Enedis
LOAD_PROFILES = {
    "C5": {"HPH": 0.20, "HCH": 0.15, "HPB": 0.35, "HCB": 0.30},
    "C4": {"HPH": 0.25, "HCH": 0.10, "HPB": 0.40, "HCB": 0.25},
    "C2": {"HPH": 0.28, "HCH": 0.08, "HPB": 0.42, "HCB": 0.22},
    "HTA": {"HPH": 0.30, "HCH": 0.07, "HPB": 0.43, "HCB": 0.20},
}


@dataclass
class DecompositionResult:
    """Resultat d'une decomposition prix complet."""

    profile: str
    period_start: datetime
    period_end: datetime

    # 7 briques en EUR/MWh
    energy_eur_mwh: float
    turpe_eur_mwh: float
    cspe_eur_mwh: float
    capacity_eur_mwh: float
    cee_eur_mwh: float
    cta_eur_mwh: float
    total_ht_eur_mwh: float
    tva_eur_mwh: float
    total_ttc_eur_mwh: float

    # Contexte
    spot_avg_eur_mwh: Optional[float] = None
    forward_ref_eur_mwh: Optional[float] = None
    volume_mwh: Optional[float] = None
    calculation_method: str = "SPOT_BASED"
    tariff_version: str = ""
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "profile": self.profile,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "energy_eur_mwh": self.energy_eur_mwh,
            "turpe_eur_mwh": self.turpe_eur_mwh,
            "cspe_eur_mwh": self.cspe_eur_mwh,
            "capacity_eur_mwh": self.capacity_eur_mwh,
            "cee_eur_mwh": self.cee_eur_mwh,
            "cta_eur_mwh": self.cta_eur_mwh,
            "total_ht_eur_mwh": self.total_ht_eur_mwh,
            "tva_eur_mwh": self.tva_eur_mwh,
            "total_ttc_eur_mwh": self.total_ttc_eur_mwh,
            "spot_avg_eur_mwh": self.spot_avg_eur_mwh,
            "forward_ref_eur_mwh": self.forward_ref_eur_mwh,
            "volume_mwh": self.volume_mwh,
            "calculation_method": self.calculation_method,
            "tariff_version": self.tariff_version,
            "warnings": self.warnings,
        }


class PriceDecompositionService:
    """Moteur de decomposition prix electricite."""

    def __init__(self, db: Session):
        self.db = db
        self._warnings: list[str] = []

    def compute(
        self,
        profile: str = "C4",
        period_start: datetime = None,
        period_end: datetime = None,
        energy_price_eur_mwh: float = None,
        volume_mwh: float = None,
        power_kw: float = None,
    ) -> DecompositionResult:
        """
        Calcule la decomposition prix pour un profil donne.

        Args:
            profile: C5, C4, C2, HTA
            period_start/end: periode de calcul
            energy_price_eur_mwh: prix energie force (sinon spot 30j)
            volume_mwh: volume annuel estime (pour CTA pro-rata)
            power_kw: puissance souscrite (pour TURPE part fixe + CTA)
        """
        self._warnings = []
        now = datetime.now(timezone.utc)
        period_start = period_start or now
        period_end = period_end or now
        # Date de reference pour le lookup tarifs (milieu de periode ou period_start)
        self._at_date = period_start

        # -- Brique 1: Energie (commodity) --
        energy = self._compute_energy(energy_price_eur_mwh)

        # -- Brique 2: TURPE (acheminement) --
        turpe = self._compute_turpe(profile, volume_mwh, power_kw)

        # -- Brique 3: CSPE / Accise --
        cspe = self._compute_cspe(profile)

        # -- Brique 4: Capacite --
        capacity = self._compute_capacity()

        # -- Brique 5: CEE --
        cee = self._compute_cee()

        # -- Brique 6: CTA (sur part fixe TURPE) --
        cta = self._compute_cta(power_kw, volume_mwh)

        # -- Total HT --
        total_ht = round(energy + turpe + cspe + capacity + cee + cta, 2)

        # -- Brique 7: TVA --
        tva = self._compute_tva(total_ht)
        total_ttc = round(total_ht + tva, 2)

        # -- Version tarif --
        tariff_version = self._get_tariff_version()

        # -- Spot reference --
        spot_avg = self._get_spot_avg()

        return DecompositionResult(
            profile=profile,
            period_start=period_start,
            period_end=period_end,
            energy_eur_mwh=round(energy, 2),
            turpe_eur_mwh=round(turpe, 2),
            cspe_eur_mwh=round(cspe, 2),
            capacity_eur_mwh=round(capacity, 2),
            cee_eur_mwh=round(cee, 2),
            cta_eur_mwh=round(cta, 2),
            total_ht_eur_mwh=total_ht,
            tva_eur_mwh=round(tva, 2),
            total_ttc_eur_mwh=total_ttc,
            spot_avg_eur_mwh=spot_avg,
            volume_mwh=volume_mwh,
            calculation_method="FORCED" if energy != (spot_avg or energy) else "SPOT_BASED",
            tariff_version=tariff_version,
            warnings=list(self._warnings),
        )

    def compute_and_store(
        self,
        org_id: int,
        site_id: int = None,
        **kwargs,
    ) -> DecompositionResult:
        """Calcule et persiste le resultat dans price_decompositions."""
        result = self.compute(**kwargs)
        record = PriceDecomposition(
            org_id=org_id,
            site_id=site_id,
            period_start=result.period_start,
            period_end=result.period_end,
            profile=result.profile,
            energy_eur_mwh=result.energy_eur_mwh,
            turpe_eur_mwh=result.turpe_eur_mwh,
            cspe_eur_mwh=result.cspe_eur_mwh,
            capacity_eur_mwh=result.capacity_eur_mwh,
            cee_eur_mwh=result.cee_eur_mwh,
            cta_eur_mwh=result.cta_eur_mwh,
            total_ht_eur_mwh=result.total_ht_eur_mwh,
            tva_eur_mwh=result.tva_eur_mwh,
            total_ttc_eur_mwh=result.total_ttc_eur_mwh,
            spot_avg_eur_mwh=result.spot_avg_eur_mwh,
            forward_ref_eur_mwh=result.forward_ref_eur_mwh,
            volume_mwh=result.volume_mwh,
            calculation_method=result.calculation_method,
            calculated_at=datetime.now(timezone.utc),
            tariff_version=result.tariff_version,
        )
        self.db.add(record)
        self.db.commit()
        return result

    # ======================================================================
    # Briques individuelles
    # ======================================================================

    def _tariff(self, tariff_type: TariffType, component: TariffComponent):
        """Lookup un tarif en vigueur a self._at_date."""
        return get_current_tariff(self.db, tariff_type, component, at_date=self._at_date)

    def _compute_energy(self, forced_price: float = None) -> float:
        """Brique 1: prix energie (commodity)."""
        if forced_price is not None:
            return forced_price
        spot = self._get_spot_avg()
        if spot is not None:
            return spot
        self._warnings.append("Aucun prix spot disponible, fallback 68 EUR/MWh")
        return 68.0

    def _compute_turpe(self, profile: str, volume_mwh: float = None, power_kw: float = None) -> float:
        """
        Brique 2: TURPE — moyenne ponderee par plage horaire selon profil.

        Formule: sum(poids_plage * tarif_plage) + part_fixe_ramenee_au_mwh
        """
        weights = LOAD_PROFILES.get(profile, LOAD_PROFILES["C4"])
        component_map = {
            "HPH": TariffComponent.TURPE_SOUTIRAGE_HPH,
            "HCH": TariffComponent.TURPE_SOUTIRAGE_HCH,
            "HPB": TariffComponent.TURPE_SOUTIRAGE_HPB,
            "HCB": TariffComponent.TURPE_SOUTIRAGE_HCB,
        }

        turpe_variable = 0.0
        for plage, poids in weights.items():
            tariff = self._tariff(TariffType.TURPE, component_map[plage])
            if tariff:
                turpe_variable += poids * tariff.value
            else:
                self._warnings.append(f"TURPE {plage} non trouve en DB")

        # Part fixe ramenee au MWh (si puissance et volume connus)
        turpe_fixe_mwh = 0.0
        if power_kw and volume_mwh and volume_mwh > 0:
            pf_tariff = self._tariff(TariffType.TURPE, TariffComponent.TURPE_PART_FIXE)
            if pf_tariff:
                # part_fixe_total = power_kw * tarif_eur_kw_an
                # ramenee au MWh = part_fixe_total / volume_mwh
                turpe_fixe_mwh = (power_kw * pf_tariff.value) / volume_mwh

        return turpe_variable + turpe_fixe_mwh

    def _compute_cspe(self, profile: str) -> float:
        """Brique 3: CSPE / accise electricite par profil."""
        cspe_map = {
            "C5": TariffComponent.CSPE_C5,
            "C4": TariffComponent.CSPE_C4,
            "C2": TariffComponent.CSPE_C2,
            "HTA": TariffComponent.CSPE_C2,  # HTA = meme taux que C2
        }
        component = cspe_map.get(profile, TariffComponent.CSPE_C4)
        tariff = self._tariff(TariffType.CSPE, component)
        if tariff:
            return tariff.value
        self._warnings.append(f"CSPE non trouvee pour profil {profile}")
        return 0.0

    def _compute_capacity(self) -> float:
        """
        Brique 4: mecanisme de capacite.

        Formule simplifiee: prix_enchere_eur_mw * coeff / 8760 heures
        98.6 EUR/MW * 1.0 / 8760 = ~0.011 EUR/MWh (quasi nul en 2026)
        """
        price_tariff = self._tariff(TariffType.CAPACITY, TariffComponent.CAPACITY_PRICE_MW)
        coeff_tariff = self._tariff(TariffType.CAPACITY, TariffComponent.CAPACITY_COEFFICIENT)
        if price_tariff and coeff_tariff:
            # EUR/MW * coeff / 8760h = EUR/MWh
            return (price_tariff.value * coeff_tariff.value) / 8760
        self._warnings.append("Capacite: tarif non trouve")
        return 0.0

    def _compute_cee(self) -> float:
        """Brique 5: CEE (pass-through fournisseur)."""
        tariff = self._tariff(TariffType.CEE, TariffComponent.CEE_OBLIGATION)
        if tariff:
            return tariff.value
        self._warnings.append("CEE: tarif non trouve")
        return 0.0

    def _compute_cta(self, power_kw: float = None, volume_mwh: float = None) -> float:
        """
        Brique 6: CTA — s'applique sur la part fixe TURPE uniquement.

        Formule: taux_cta * part_fixe_turpe_eur_kw_an * power_kw / volume_mwh
        Si pas de puissance/volume, approximation via ratio moyen.
        """
        cta_tariff = self._tariff(TariffType.CTA, TariffComponent.CTA_TAUX)
        if not cta_tariff:
            self._warnings.append("CTA: taux non trouve")
            return 0.0

        taux_pct = cta_tariff.value / 100  # 27.04% -> 0.2704

        pf_tariff = self._tariff(TariffType.TURPE, TariffComponent.TURPE_PART_FIXE)
        if not pf_tariff:
            self._warnings.append("CTA: TURPE part fixe non trouvee")
            return 0.0

        if power_kw and volume_mwh and volume_mwh > 0:
            # CTA = taux% * (puissance * tarif_fixe) / volume
            cta_total = taux_pct * power_kw * pf_tariff.value
            return cta_total / volume_mwh

        # Approximation: ratio moyen power/volume pour un site C4 type
        # 250 kW / 2000 MWh = 0.125 kW/MWh
        ratio_kw_per_mwh = 0.125
        self._warnings.append("CTA: approximation ratio puissance/volume (0.125 kW/MWh)")
        return taux_pct * pf_tariff.value * ratio_kw_per_mwh

    def _compute_tva(self, total_ht: float) -> float:
        """Brique 7: TVA a taux normal sur la totalite."""
        tariff = self._tariff(TariffType.TVA, TariffComponent.TVA_NORMAL)
        if tariff:
            return total_ht * tariff.value / 100
        self._warnings.append("TVA: taux non trouve, fallback 20%")
        return total_ht * 0.20

    # ======================================================================
    # Helpers
    # ======================================================================

    def _get_spot_avg(self) -> Optional[float]:
        """Moyenne spot 30j depuis mkt_prices."""
        try:
            svc = MarketDataService(self.db)
            return svc.get_spot_average(days=30)
        except Exception:
            return None

    def _get_tariff_version(self) -> str:
        """Version du jeu de tarifs utilise."""
        cspe = self._tariff(TariffType.CSPE, TariffComponent.CSPE_C4)
        if cspe:
            return cspe.version
        return "unknown"
