# Followup — Consolidation source-of-truth tarifs (P0 bloquant)

**Origine** : Audit Agents SDK — Phase 0 (2026-04-24) faille #2 + Ajustement 2 addendum
**Sévérité** : P0 — bloque création skill `tariff_constants`
**Hors scope** : audit agents (prérequis à traiter avant Phase 3)

## Problème

Deux sources de vérité concurrentes pour TURPE / accises / CTA / TICGN :

| Source | Format | Utilisée par |
|---|---|---|
| `backend/config/tarifs_reglementaires.yaml` | YAML versionné (MR2026-04) | ParameterStore, `regulatory.py` V120 |
| `backend/services/billing_engine/catalog.py` | Python hardcodé | Shadow billing, certains recalcs |

**Divergences connues** (V120 session 15/04) :
- Accise élec 2025 : YAML était incomplet (5 mois gap), `catalog.py` avait les bonnes valeurs → fix queue 1
- TURPE sans version dans nom YAML (`turpe` générique) vs `catalog.py` qui a TURPE 7
- CTA / TICGN : double vérité

## Pourquoi bloquant pour skill `tariff_constants`

Créer le skill = **cristalliser** l'état actuel comme SoT pour tous les agents. Si les 2 sources divergent encore, le skill :
- Soit reflète YAML → `bill-intelligence` (qui utilise `catalog.py`) sera en désaccord
- Soit reflète `catalog.py` → `regulatory-expert` (qui utilise YAML via ParameterStore) sera en désaccord
- Soit reflète les 2 → le skill devient ambigu et inutilisable

## Action proposée

### Étape 1 — Audit exhaustif des divergences

```bash
# Comparaison systématique YAML vs catalog.py
# Attendu : rapport docs/audit/tarifs_sot_divergences.md
```

Produire tableau par grille :
- TURPE 7 (HPH, HCH, HPB, HCB, Pointe, composante puissance)
- Accises élec T1/T2 (fév 2025, août 2025, fév 2026)
- Accise gaz (T1 à T4 ATRD)
- CTA (ancien 21.93%, nouveau fév 2026)
- TICGN (deprecated)
- TVA (5.5/20)

### Étape 2 — Consolidation YAML comme SoT unique

- Enrichir YAML de tous les champs manquants détectés
- Migrer `catalog.py` pour LIRE depuis YAML (via ParameterStore) au lieu de hardcoder
- Source-guard : test qui échoue si `catalog.py` réintroduit un literal tarifaire hors ParameterStore

### Étape 3 — Créer skill `tariff_constants` (débloque audit agents Phase 3)

- Skill pointe uniquement vers le YAML
- Référence explicite : `backend/config/tarifs_reglementaires.yaml` SoT

## Lien avec audit agents SDK

- **Phase 3** catalogue bloquée tant que ce followup pas clos
- **Alternative temporaire** : créer skill `tariff_constants` avec un warning "à consolider" et noter la dette — **refusé par arbitrage addendum Ajustement 2** (pas de cristallisation)

## Owner

À assigner. Estimation : ~4-6h (audit + migration + tests).

## Références

- V120 findings YAML : `project_agent_sdk_migration_2026_04_15.md` section "Regulatory Analyst audit-cesures"
- Skill Paperclip KB : `~/.paperclip/instances/default/promeos_kb/` (réf historique, pas exécutable)
