"""Catalogues i18n par locale — Phase 9.C narrative-sol2.

Chaque locale expose un dict `CATALOG: dict[str, str]` avec les clés
canoniques narrative et leur traduction. Les valeurs peuvent contenir
des placeholders `{name}` interpolés via `i18n.t(key, locale, **kwargs)`.

Convention de clés : namespace dot-separated.
- `stable.{typology}` : phrases de stabilité
- `composer.{trigger}.{typology}` : phrases événementielles
- `format.eur_short` / `format.pct_short` : formats numériques
- `role.{role}.{typology}` : libellés rôle persona
"""
