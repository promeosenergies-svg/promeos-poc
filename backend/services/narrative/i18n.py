"""i18n infrastructure narrative — Sprint Refonte Narrative dynamique Phase 9.C.

Infrastructure d'internationalisation minimale pour le sprint narrative.

## Périmètre Phase 9.C (MVP)

- `Locale` enum : FR (par défaut) + EN (squelette à enrichir V2)
- `t(key, locale, **kwargs)` : helper de résolution avec fallback FR safe
- Catalogue de chaînes par locale dans `i18n_locales/{fr,en}.py`
- Source-guards : couverture clés FR/EN équivalente

## Hors scope Phase 9.C

- Migration des composers vers `t()` partout — gros refactor reporté V2.
  Le sprint a livré environ 80 chaînes FR hardcodées dans sentence_composer,
  persona_context, tone_variator. Migrer toutes nécessite un sprint dédié
  + retest panel utilisateur avec EN locale (≠ Phase 5 qui est FR-only).
- Détection de la locale utilisateur (Accept-Language header, User.locale field).
  Phase 9.C expose la fonction `t()` ; le wiring locale-aware viendra V2.
- ES/IT/DE/etc. — Phase 9.C cible uniquement FR + EN.

## Usage runtime

```python
from services.narrative.i18n import t, Locale

# Résolution explicite
msg = t("stable.grand_groupe", Locale.FR)
# Avec interpolation
msg = t("phrase_drift.grand_groupe", Locale.FR, sites_count=3, source="RegOps")
# Fallback automatique sur FR si clé manquante en EN
msg = t("non_existant_key", Locale.EN)  # → fallback FR ou key littérale
```

Ref : audit final ticket BL-5 + sprint narrative-sol2 Phase 9.C.
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class Locale(str, Enum):
    """Locales supportées Phase 9.C.

    FR : locale par défaut, complète (toutes les chaînes du sprint).
    EN : squelette V2 — clés présentes mais traductions partielles à enrichir.
    """

    FR = "fr"
    EN = "en"


# Locale par défaut si aucune passée à t()
DEFAULT_LOCALE: Locale = Locale.FR


def t(key: str, locale: Locale = DEFAULT_LOCALE, **kwargs: Any) -> str:
    """Résout une clé i18n vers la chaîne localisée.

    Args:
        key: clé canonique (ex: `stable.grand_groupe`, `composer.dt_drift.commerce`).
            Format dot-separated namespace.
        locale: locale cible (Locale.FR / Locale.EN). Défaut FR.
        **kwargs: variables d'interpolation `{name}` substituées dans la chaîne.

    Returns:
        Chaîne traduite et interpolée. Si clé absente :
        1. Fallback sur Locale.FR
        2. Si encore absente → retourne la clé littérale (signal de bug)
        3. Erreurs d'interpolation (KeyError sur kwargs manquants) → chaîne brute

    Examples:
        >>> t("stable.grand_groupe", Locale.FR)
        'Votre patrimoine tient sa trajectoire cette semaine — ...'
        >>> t("composer.dt_drift.commerce", Locale.FR, activity="boulangerie")
        'Votre boulangerie consomme ...'
    """
    catalog = _CATALOGS.get(locale, {})
    template = catalog.get(key)

    # Fallback sur FR si clé absente dans la locale demandée
    if template is None and locale != Locale.FR:
        fr_catalog = _CATALOGS.get(Locale.FR, {})
        template = fr_catalog.get(key)

    # Si toujours absente — signal de bug, retourner la clé littérale
    if template is None:
        return f"[{key}]"

    # Interpolation safe — KeyError sur var manquante ne lève pas
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError):
        return template  # template brut si interpolation échoue


# ─── Catalogues lazy-loaded ────────────────────────────────────────────────


_CATALOGS: dict[Locale, dict[str, str]] = {}


def _load_catalog(locale: Locale) -> None:
    """Lazy-load d'un catalogue depuis i18n_locales/{fr,en}.py."""
    if locale in _CATALOGS:
        return
    if locale == Locale.FR:
        from services.narrative.i18n_locales.fr import CATALOG as FR_CATALOG

        _CATALOGS[Locale.FR] = FR_CATALOG
    elif locale == Locale.EN:
        from services.narrative.i18n_locales.en import CATALOG as EN_CATALOG

        _CATALOGS[Locale.EN] = EN_CATALOG


# Auto-load des deux catalogues à l'import (catalogues petits, OK runtime)
_load_catalog(Locale.FR)
_load_catalog(Locale.EN)


def list_keys(locale: Locale = DEFAULT_LOCALE) -> list[str]:
    """Liste les clés disponibles dans une locale (debug / introspection)."""
    return sorted(_CATALOGS.get(locale, {}).keys())


__all__ = [
    "Locale",
    "DEFAULT_LOCALE",
    "t",
    "list_keys",
]
