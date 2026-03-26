"""
PROMEOS -- Prix par defaut quand aucune source n'est disponible.
Source unique. Tous les services doivent importer depuis ici.

Cascade get_reference_price() :
  1. Contrat actif (EnergyContract.price_ref_eur_per_kwh)
  2. Moyenne spot 30j (mkt_prices EPEX Spot FR)
  3. SiteTariffProfile
  4. Fallback ci-dessous (devrait rarement etre atteint)
"""

# Prix fourniture par defaut (EUR/kWh) -- utilise quand :
# - Pas de contrat actif
# - Pas de prix marche disponible
# - Pas de tariff profile
# Ancien fallback 0.18 EUR/kWh retire (2.6x trop haut vs EPEX Spot ~68 EUR/MWh)
DEFAULT_PRICE_ELEC_EUR_KWH = 0.068  # 68 EUR/MWh — aligne sur EPEX Spot moyen 2025
DEFAULT_PRICE_GAZ_EUR_KWH = 0.045  # 45 EUR/MWh — aligne sur PEG moyen 2025
DEFAULT_PRICE_HC_EUR_KWH = 0.055  # Heures creuses — proportionnel


def get_default_price(energy_type: str = "ELEC") -> float:
    """Retourne le prix par defaut pour un vecteur energetique."""
    if energy_type.upper() == "GAZ":
        return DEFAULT_PRICE_GAZ_EUR_KWH
    return DEFAULT_PRICE_ELEC_EUR_KWH
