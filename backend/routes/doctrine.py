"""Route API doctrine PROMEOS — expose le dictionnaire acronymes SoT.

Sprint Grammaire v1 Phase 1.1 (2026-05-09).
Consommée par le hook frontend useAcronymes + le composant <Term acronyme="..."/>
Sol v1.1.

Endpoint public (lecture seule, pas d'org-scoping requis — données statiques
réglementaires sans PII). Pas de rate-limit : données immuables en cache mémoire.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/v1/doctrine", tags=["doctrine"])

_CACHE: dict | None = None
_YAML_PATH = Path(__file__).resolve().parents[1] / "config" / "acronymes_doctrine.yaml"


def _load_acronymes() -> dict:
    """Charge le YAML acronymes_doctrine (cache module-scope, 1 lecture par démarrage)."""
    global _CACHE
    if _CACHE is None:
        if not _YAML_PATH.exists():
            raise FileNotFoundError(f"acronymes_doctrine.yaml introuvable : {_YAML_PATH}")
        with open(_YAML_PATH, "r", encoding="utf-8") as fh:
            _CACHE = yaml.safe_load(fh)
    return _CACHE


@router.get(
    "/acronymes",
    summary="Dictionnaire acronymes SoT (complet)",
    response_description="YAML acronymes_doctrine sérialisé en JSON",
)
def get_acronymes() -> dict:
    """Retourne le dictionnaire acronymes SoT complet (cache mémoire, 1ère lecture).

    Inclut version, description, et tous les acronymes avec leurs champs
    (short, long, narrative, source, doctrine_ref, pillar, jalons?).
    """
    return _load_acronymes()


@router.get(
    "/acronymes/{key}",
    summary="Entrée acronyme spécifique",
    response_description="Entrée acronyme ou 404 si inconnue",
)
def get_acronyme(key: str) -> dict:
    """Retourne l'entrée d'un acronyme spécifique (insensible à la casse).

    Args:
        key: Code acronyme (ex: TURPE, DT, BACS). Case-insensitive.

    Returns:
        Dictionnaire de l'entrée acronyme.

    Raises:
        HTTPException 404 si l'acronyme est absent du dictionnaire.
    """
    data = _load_acronymes()
    entry = data.get("acronymes", {}).get(key.upper())
    if not entry:
        raise HTTPException(
            status_code=404,
            detail=f"Acronyme '{key.upper()}' inconnu — non répertorié dans acronymes_doctrine.yaml",
        )
    return entry
