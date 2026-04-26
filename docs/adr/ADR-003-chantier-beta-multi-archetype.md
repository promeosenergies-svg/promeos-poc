# ADR-003 — Chantier β multi-archetype dynamique

**Statut** : Proposé
**Date** : 2026-04-26
**Sprint** : S3 (semaines 6-7)
**Personnes impliquées** : Amine (founder), Claude architect-helios

## Contexte

Test doctrinal T3 (grand écart) FAIL universel — produit aujourd'hui copy "vos bureaux" pour usine, benchmark ADEME bureau pour agroalim, KPI tertiaire affiché à industriel. Principe 3 (grand écart compatible) et principe 12 (sachant et surtout non-sachant) non incarnés.

**Inventaire Sprint 0bis** : multi-archetype β couvert à **85% déjà existant** :
- `services/flex/archetype_resolver.py` (8 archetypes Flex)
- `services/archetype_recommendation.py` (15 archétypes × 732 NAF)
- `docs/base_documentaire/naf/naf_archetype_mapping/archetypes_energy_v1.json` (15 archétypes × 4 benchmarks ADEME ODP/ELMAS/Enertech)
- `docs/base_documentaire/naf/naf_archetype_mapping/naf_to_archetype_v1.json` (mapping bidirectionnel 732 NAF)
- `utils/naf_resolver.py` resolve_naf_code() canonique
- 3 personas démo : investisseur + Jean-Marc CFO ETI tertiaire + Marie DAF tertiaire 5 sites

**Le travail S3 est 80% surfacage + 20% extension narrative_generator + seed orchestrator multi-pack.**

## Décision

### Service `backend/services/narrative/narrative_generator.py` (ADR-001) — branche archetype

Resolver canonique unique : `resolve_archetype(org_id, site_id?) -> Archetype` consolide les 4 sources existantes :
- `naf_resolver.resolve_naf_code()` (NAF brut)
- `archetype_recommendation` (15 archétypes documentés)
- `archetype_resolver.flex_archetype()` (existant 8 valeurs Flex)
- Heuristiques surface/multi-site/saisonnalité

Output enum `Archetype` 5 valeurs **canonical pour démo juillet** (consolidation des 15 archétypes documentés en 5 packs démo) :
```
TERTIAIRE_MIDMARKET    -- Marie 5 sites (NAF 6820/41xx/43xx)
INDUSTRIEL_AGROALIM    -- Energimat (NAF 10xx/11xx)
HOTELIER_SAISONNIER    -- (NAF 5510/5520)
COLLECTIVITE_MULTI_ECOLES  -- (NAF 84xx/85xx)
MONO_SITE_PME          -- wedge Sirene <3min (NAF divers)
```
Extensibilité : enum extensible, mais démo gelée à 5 (chacun seedé).

### Génération narrative par archetype

`narrative_generator.generate_page_narrative(org_id, page_key, persona, archetype, ...)` branche logique :

```
narrative_builders/
  __init__.py
  base.py                    -- NarrativeBuilder ABC
  tertiaire_midmarket.py
  industriel_agroalim.py
  hotelier_saisonnier.py
  collectivite_multi_ecoles.py
  mono_site_pme.py
```

Chaque builder implémente `build(page_key, persona, context) -> Narrative`. Méthode commune : `compose_kicker()`, `compose_title()`, `compose_narrative()`, `select_kpis()`, `select_benchmark_set()`.

Aucun `if archetype == X` dans les pages frontend. Aucun calcul frontend. Backend renvoie narrative finale prête à afficher.

### KPIs prioritaires variables par archetype

Mapping canonical dans `backend/services/narrative/kpi_priorities.yaml` (ParameterStore versionné) :

| Archetype | KPI 1 | KPI 2 | KPI 3 |
|-----------|-------|-------|-------|
| TERTIAIRE_MIDMARKET | Trajectoire 2030 (DT) | Économies factures détectées | Mutualisation potentielle €/an |
| INDUSTRIEL_AGROALIM | Revenus flexibilité éligibles €/an | Intensité énergétique kWh/€ CA | Trajectoire 2030 process |
| HOTELIER_SAISONNIER | Saisonnalité écart vs N-1 | EUI vs benchmark hôtel ADEME | Échéances réglementaires |
| COLLECTIVITE_MULTI_ECOLES | Budget consommé % allocation | Confort hiver DJU | Dossiers CEE en cours |
| MONO_SITE_PME | Anomalie facture détectée € | Tarif optimal vs payé | 1ère échéance réglementaire |

### Benchmarks adaptés

`benchmarks_resolver.get_benchmark_set(archetype, building_type)` — wrap `archetypes_energy_v1.json` existant :
- Tertiaire : ADEME ODP bureau OID 146 kWhEF/m²/an, école, hôtel
- Industriel : ADEME industrie par NAF + IPE secteur
- Collectivité : panel ADEME + DGEC public
- Mono-site PME : fallback intensité moyenne NAF

### Vocabulaire ajusté — table de transposition copy

`backend/config/copy_transposition.yaml` (ParameterStore) — multi-niveau :
```yaml
target_lexicon:
  daf:        # parle € HT
    consumption: "facture"
    drift: "dérive budgétaire"
    flex_revenue: "revenu additionnel HT"
  operator:   # parle kWh
    consumption: "consommation"
    drift: "dérive de baseline"
    flex_revenue: "revenu effacement"
  director:   # parle ROI
    consumption: "poste énergie"
    drift: "écart trajectoire"
    flex_revenue: "ROI flexibilité"
```
Persona déduite de `User.role` + `Org.profile`. Builder narrative consomme le lexique pertinent.

### Seed démo `services/demo_seed/orchestrator.py` étendu

5 packs au lieu d'1 :
```
python -m services.demo_seed --pack helios --archetype tertiaire_midmarket --size S --reset
python -m services.demo_seed --pack helios --archetype industriel_agroalim --size M --reset
python -m services.demo_seed --pack helios --archetype hotelier_saisonnier --size S --reset
python -m services.demo_seed --pack helios --archetype collectivite_multi_ecoles --size S --reset
python -m services.demo_seed --pack helios --archetype mono_site_pme --size XS --reset
```
Démo juillet : pack `tertiaire_midmarket` (Marie + Jean-Marc) chargé par défaut. Investisseur démo bouton "Switch archetype" qui re-seed + reload — preuve grand écart en live.

### Endpoint contrat

`GET /api/archetype/current?org_id=X` → `{ archetype, naf_code, confidence, fallback_reason? }`
`POST /api/archetype/override?org_id=X` (DEMO_MODE only) → permet switch démo investisseur

L'endpoint `/api/pages/{page_key}/briefing` (ADR-001) accepte `archetype` query param. Si absent : auto-resolve.

## Conséquences

- **Positives** : T3 (grand écart) PASS, démo investisseur "même produit, 5 archetypes" devient argument différenciation #1, mutualisation existante ADEME ODP enfin surfacée par typologie
- **Négatives / risques** : 5 builders × 10 page_keys × 2 personas = 100 templates narrative à écrire. Mitigation : builder `base.py` template par défaut + override seulement quand pertinent (estimation 30 overrides spécifiques au max). Risque divergence copy : tests `test_copy_transposition_lexicon_used` regex sur narrative renvoyée
- **Migration** : S3.1 resolver + enum + builders ABC → S3.2 builders tertiaire + industriel (couvre Marie + Energimat) → S3.3 builders hôtelier + collectivité + mono-site → S3.4 seed orchestrator 5 packs + bouton switch démo

## Alternatives considérées

1. **Réutiliser les 8 archetypes Flex tels quels** — rejeté : taille trop fine pour narrative globale (ex `INDUSTRIE_FROIDS_PROCESS` vs `INDUSTRIE_PROCESS_THERMIQUE`). Garde 5 archetypes narrative + mapping vers 8 archetypes Flex pour Flex pillar uniquement
2. **Templates narrative côté frontend selon archetype** — rejeté : viole §8.1, multiplie divergence
3. **Génération LLM live de la narrative** — différé : non-déterministe pour démo, latence, coût. Roadmap S7+ post-démo pour personnalisation fine

## Tests / validation

- T3 (grand écart) automatisé : pour les 5 archetypes seedés, snapshot pages Cockpit/Patrimoine/Conformité, assert vocabulaire et benchmarks distincts (regex anti "vos bureaux" dans pack industriel)
- `test_archetype_resolver_canonical` : input NAF → output archetype déterministe stable
- `test_kpi_priorities_yaml_valid_schema` : ParameterStore versionning
- `test_copy_transposition_no_leak` : lexique daf ne fuit pas dans narrative operator et inversement
- `test_seed_5_packs_complete` : chaque pack seed sans erreur + RegAssessment/Site/Contract minimum présents

## Doctrine compliance §11.3

- **Principes respectés** : 3 (grand écart), 8 (simplicité — vocabulaire ajusté = moins friction), 10 (transformation contextualisée), 12 (non-sachant servi par vocabulaire adapté)
- **Anti-patterns évités** : §6.3 copy "vos bureaux" pour usine, §6.4 module mono-archetype implicite, §6.5 logique frontend
- **Personas servis** : Marie (tertiaire midmarket), Jean-Marc (tertiaire ETI vue COMEX), investisseur (démo 5 archetypes en live)

## Référence cross-ADR

ADR-001 (narrative_generator branche archetype), ADR-002 (events filtrés/priorisés par archetype — un industriel reçoit événements flexibilité, tertiaire reçoit DT), ADR-004 (transposition acronymes peut varier par archetype). Memory : `project_usage_fil_conducteur.md`, `project_promeos_tpe_pme_copro.md`, `docs_skills_kb_system.md`. Doctrine §3 P3, §9.3 chantier β.

## Délégations sortantes

- Implémentation S3 : `implementer` (chaîné `test-engineer` + `code-reviewer` + `qa-guardian` pre-merge)
- Validation archétypes énergie : `ems-expert` + `regulatory-expert`
- Seed démo 5 packs : `data-connector` (orchestrateur seed)
