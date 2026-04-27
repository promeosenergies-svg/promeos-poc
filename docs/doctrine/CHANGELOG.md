# Changelog Doctrine PROMEOS Sol

## v1.1 — 2026-04-27

Première version consolidée. Source d'autorité produit + UX + data + engineering.

- 13 principes cardinaux
- Contrat de confiance data (statuts obligatoires)
- Doctrine KPI (fiche YAML obligatoire)
- Grammaire éditoriale (§9)
- SolEventCard typé (§10)
- Architecture fonctionnelle 8 modules (§11)
- Standard d'erreur API (§12.2)
- Anti-patterns explicites (§13)
- Tests doctrinaux (§14)
- Checklist QA zéro issue (§15)
- Governance engineering + critères de rejet PR (§16)
- Definition of Done produit (§18)

Hash SHA256 figé : voir `backend/doctrine/__init__.py` (`DOCTRINE_SHA256_FROZEN`).
Valeur v1.1 : `0b08266d1e613bfcd547dbb937762f8e7a09f51191830e2426055f5cdff55d1e`

### Dette structurelle reconnue (à résorber en sprint P1)

148 occurrences de constantes inviolables (CO₂, accises, pénalités DT, prix fallback) actuellement
hard-codées dans 22 fichiers backend (services, routes, regops, billing_engine, narrative,
demo_seed). Ces fichiers sont temporairement listés dans `tests/doctrine/test_constants_not_redefined.py`
sous `LEGACY_DEBT_ALLOWED` afin de ne pas bloquer le sprint structurel P0.

Sprint P1 : migration progressive `from backend.doctrine.constants import …` puis suppression
de `LEGACY_DEBT_ALLOWED`.
