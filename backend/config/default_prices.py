"""
PROMEOS -- Prix par defaut quand aucune source n'est disponible.
Source unique. Tous les services doivent importer depuis ici.
"""

# Prix fourniture par defaut (EUR/kWh) -- utilise quand :
# - Pas de contrat actif
# - Pas de prix marche disponible
# - Pas de tariff profile
DEFAULT_PRICE_ELEC_EUR_KWH = 0.18
DEFAULT_PRICE_GAZ_EUR_KWH = 0.09
DEFAULT_PRICE_HC_EUR_KWH = 0.13


def get_default_price(energy_type: str = "ELEC") -> float:
    """Retourne le prix par defaut pour un vecteur energetique."""
    if energy_type.upper() == "GAZ":
        return DEFAULT_PRICE_GAZ_EUR_KWH
    return DEFAULT_PRICE_ELEC_EUR_KWH
