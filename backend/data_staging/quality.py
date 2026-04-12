"""
SF5 — Mapping qualité : statut brut → (quality_score, is_estimated).

Sources :
- R4x : statut_point (R/C/S/T/F/G/D/H/K/P/E)
- R50 : indice_vraisemblance (0/1)
- R171 : pas d'indicateur → 0.90
- R151 PMAX : pas d'indicateur → 0.90
"""

# R4x statut_point → (quality_score, is_estimated)
_R4X_QUALITY = {
    "R": (1.00, False),  # Réel
    "C": (0.95, False),  # Corrigé
    "S": (0.90, False),  # Coupure réseau
    "T": (0.90, False),  # Coupure réseau
    "F": (0.90, False),  # Coupure réseau
    "G": (0.90, False),  # Coupure réseau
    "D": (0.85, False),  # Import manuel Enedis
    "H": (0.80, True),  # Reconstitué (DST/conversion)
    "K": (0.75, True),  # Dérivé d'autres courbes
    "P": (0.70, True),  # Reconstitué + coupure
    "E": (0.60, True),  # Estimé
}

_R4X_DEFAULT = (0.50, True)


def quality_r4x(statut_point: str | None) -> tuple[float, bool]:
    """Retourne (quality_score, is_estimated) pour un point R4x."""
    if not statut_point:
        return _R4X_DEFAULT
    return _R4X_QUALITY.get(statut_point.strip().upper(), _R4X_DEFAULT)


def quality_r50(indice_vraisemblance: str | None) -> tuple[float, bool]:
    """Retourne (quality_score, is_estimated) pour un point R50."""
    iv = str(indice_vraisemblance).strip() if indice_vraisemblance is not None else ""
    if iv == "0":
        return (1.00, False)
    if iv == "1":
        return (0.70, False)
    return (0.50, True)  # Inconnu → conservateur, marquer estimé


def quality_r171() -> tuple[float, bool]:
    """R171 : pas d'indicateur qualité → 0.90 par défaut."""
    return (0.90, False)


def quality_r151_pmax() -> tuple[float, bool]:
    """R151 PMAX : pas d'indicateur qualité → 0.90 par défaut."""
    return (0.90, False)
