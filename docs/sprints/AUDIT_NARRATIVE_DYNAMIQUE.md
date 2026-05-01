# Audit Narrative dynamique Synthèse stratégique

> Audit read-only effectué avant le sprint d'exécution Narrative dynamique.
> Branche : `claude/refonte-sol2`
> Date : 2026-05-01
> Pré-condition : sprint Refonte Cockpit Dual Sol2 validé (commit `8f9994a6`).

## Index des outputs

Tous les artefacts sont dans `docs/sprints/AUDIT_NARRATIVE_DYNAMIQUE/` :

### outputs/

- `narrative_files.txt` : cartographie 68 fichiers BE+FE liés narrative
- `narrative_size.txt` : 3 069 lignes pour `narrative_generator.py`
- `narrative_signatures.txt` : 30 signatures (25 def + 5 class)
- `narrative_consumers.txt` : endpoint unique `/api/pages/{page_key}/briefing` + 4 pages FE consomment
- `typology_audit.txt` : NAF stocké sur Site/EJ mais pas mappé en typologie
- `persona_audit.txt` : 2 personas (`daily`/`comex`) — pas de stockage user.role
- `triggers_audit.txt` : 0 keyword cible matché (drift_pct, purchase_window, etc.)
- `event_push_audit.txt` : `event_bus.compute_events` + 9 detectors existent + `weekly_deltas` exposé
- `narrative_complexity.txt` : 25 fonctions, 5 classes, 206 f-strings, 124 if
- `narrative_tests.txt` : 1 test BE dédié + 4 tests FE briefing

### samples/

- `narrative_generator_current.py` : snapshot 3 069 lignes
- `narrative_helios_daily_full.json` : payload complet persona daily
- `narrative_helios_comex_full.json` : payload complet persona comex
- `narrative_helios_daily_text.txt` : narrative Marie 8h45 (~30 mots, 2 phrases)
- `narrative_helios_comex_text.txt` : narrative Jean-Marc CFO (~50 mots, 3 phrases)
- `narrative_helios_text.txt` : alias = comex (cible prompt)
- `narrative_today.txt` / `narrative_tomorrow.txt` : test dynamique J vs J+1

### findings/

- `narrative_quality_helios.md` : évaluation qualité 5/10 vs doctrine §11.3
- `narrative_dynamic_test.txt` : verdict `simulate_date` accepté mais ignoré

## Synthèse pour Claude (instance externe)

### Ce qui existe déjà (dans le code)

- Module `narrative_generator.py` : **3 069 lignes**, **25 fonctions**, **5 classes**
- Endpoint canonique : `/api/pages/{page_key}/briefing?org_id=X&persona=daily|comex`
- 9 builders enregistrés dans `_BUILDERS` (cockpit_daily, cockpit_comex, patrimoine, conformite, bill_intel, achat, monitoring, diagnostic, anomalies)
- 2 personas typés : `Persona = Literal["daily", "comex"]`
- Champ `narrative_tone: NarrativeTone` exposé dans le payload (P0-D densification)
- Helper `_compute_tone(non_conformes, a_risque, score, urgency_critical)` calculé per-builder
- Détection typologie NAF :
  - Champ `naf_code` stocké sur `Site`, `EntiteJuridique`, `Patrimoine`, `KBMappingCode`, `Segmentation`
  - Helper `backend/utils/naf_resolver.py` : `naf_prefix()`, `resolve_naf_code()` (51 lignes)
  - **Mais aucun mapping NAF → typologie** dans `backend/doctrine/`
- Push événementiel :
  - `_facts.weekly_deltas` exposé : 4 métriques (`exposure_eur`, `potential_mwh_year`, `sites_in_drift`, `compliance_score`)
  - `_facts.consumption.weekly_breakdown[]` (Phase 27, 7 entries jour-par-jour)
  - `event_bus.compute_events` orchestre **9 detectors** (consumption_drift, contract_renewal, compliance_deadline, billing_anomaly, asset_registry_issue, action_overdue, data_quality_issue, flex_opportunity, market_window)
  - Champ `events: tuple[SolEventCard, ...]` exposé dans le payload narrative
- Système de transformation acronymes : `doctrine.acronyms.transform_acronym` existe mais
  appliqué uniquement aux **titres d'actions**, pas au corps narrative

### Ce qui manque (vs cible doctrine §11.3)

| Cible | Statut |
|---|---|
| **3 typologies organisationnelles** (grand groupe / commerce / ERP) | ❌ Mapping `naf_to_typology.py` absent |
| **Mapping NAF → typologie** dans `backend/doctrine/` | ❌ À créer |
| **6 déclencheurs hiérarchisés explicites** (priorité primary/secondary) | ❌ 9 detectors existent mais pas hiérarchisation produit-cible |
| **Variation lexicale par typologie** | ❌ Templates uniques `f"..."` dans builders |
| **Mention persona** (nom + rôle dans la narrative) | ❌ "Vous avez" générique |
| **Push événementiel "+X vs S-1" injecté dans body narrative** | ❌ `weekly_deltas` exposé mais non consommé |
| **Variation tonale alarme/stable/amélioration** | ⚠️ `narrative_tone` calculé mais pas exploité côté lexique |
| **Acronymes glossés inline dans body** | ❌ Acronymes bruts (Décret n°2019-771, CEE BAT-TH) |
| **Param `simulate_date` fonctionnel** | ❌ Accepté HTTP 200 mais ignoré → impossible de tester la dynamique |

### Points de rupture (les 3 plus impactants)

#### 1. Pas de mapping NAF → typologie organisationnelle

Le NAF est stocké à 5 endroits du modèle et `naf_resolver.py` sait l'extraire,
mais **aucun mapping `NAF → {grand groupe, commerce, ERP, industrie}`** n'existe
dans `backend/doctrine/`. Conséquence : le `narrative_generator` ne peut pas
varier le lexique selon le secteur.

**Effort estimé** : créer `backend/doctrine/naf_to_typology.py` (~80 lignes,
table NAF → 3-5 typologies) + tests source-guards.

#### 2. Push événementiel "+X vs S-1" exposé mais non consommé par narrative

`_facts.weekly_deltas` (Phase 3.3 sprint Cockpit dual) expose 4 métriques avec
delta vs S-1. **Mais la narrative ne les injecte pas**. Le payload retourne
`events: [...]` séparément (vu dans capture sample), mais ces events ne sont
pas tissés dans le BODY narrative.

Conséquence : un user qui consulte 2 jours d'affilée la Synthèse stratégique
voit le même texte sauf si la DB a évolué — aucune **mémoire temporelle
visible** dans la narrative.

**Effort estimé** : ajouter helper `_inject_weekly_push(narrative, weekly_deltas)`
qui prepend ou postfixe "+X vs S-1" dans le body. ~50 lignes + tests.

#### 3. Hiérarchisation produit-cible des déclencheurs absente

`event_bus.compute_events` retourne une liste **non hiérarchisée** d'events
détectés. La doctrine cible attend **6 déclencheurs hiérarchisés** avec :
- 1 primary trigger (le plus saillant)
- 2 secondary triggers (contexte)
- 3 tertiary triggers (background)

**Effort estimé** : ajouter `services/narrative/trigger_prioritizer.py` (~120 lignes)
qui mappe les 9 detectors actuels aux 6 cibles + hiérarchise par sévérité +
expose `primary_trigger_text`, `secondary_triggers[]` au payload narrative.

### Recommandation pour sprint d'exécution

| Phase | Effort | Périmètre |
|---|---:|---|
| 1 — Typologie NAF | 4-6 h | Mapping NAF→typologie + helper resolve_typology + 3 templates lexicaux par typologie |
| 2 — Push événementiel | 4-6 h | Injection `weekly_deltas` dans body narrative + variation lexicale par direction (haussier/baissier/stable) |
| 3 — Hiérarchisation déclencheurs | 6-8 h | trigger_prioritizer + mapping 9 detectors → 6 cibles + primary/secondary/tertiary |
| 4 — Mention persona + variation tonale | 3-4 h | Injection prénom + rôle dans body, exploitation `narrative_tone` (alarme/stable/amélioration) |
| 5 — Source-guards + tests | 4-6 h | 8-10 source-guards : test_narrative_typology_variation, test_narrative_weekly_push_present, test_narrative_persona_named, etc. |
| 6 — `simulate_date` paramètre | 2-3 h | Implémentation effective + test qualitatif J vs J+1 vs J+30 |

**Total effort estimé** : **23-33 h** (3-5 semaines à 8h/semaine).

**Risques identifiés** :

1. **Doctrine incomplète sur les 3 typologies** : MVP attendu = grand groupe / commerce / ERP, mais HELIOS S est un mix tertiaire (bureau + hôtel + école + entrepôt). Le mapping doit traiter le **mix** au niveau Organisation, pas du Site individuel.
2. **Couplage event_bus ↔ narrative** : ajouter `trigger_prioritizer` dans `services/narrative/` risque de dupliquer la logique de `event_bus.compute_events`. Préférer un consumer pattern : narrative APPELLE compute_events + filtre/priorise.
3. **Acronymes glossés dans body** : `transform_acronym` fonctionne sur titres mais sur body c'est plus subtil (ne pas casser le sourçage réglementaire "Décret n°2019-771"). À cadrer.
4. **Compatibilité Phase 4 panel humain** : la narrative actuelle est testée par 1 test BE seulement. Le sprint doit livrer ≥ 8 source-guards pour permettre le panel humain Q3 sans risque de régression silencieuse.

## Compteurs synthétiques

| Métrique | Valeur |
|---|---:|
| `narrative_generator.py` lignes | **3 069** |
| Builders enregistrés `_BUILDERS` | 9 |
| Personas typés | 2 (`daily`/`comex`) |
| Detectors event_bus | 9 |
| Cibles narrative §11.3 (déclencheurs) | 6 |
| Mapping NAF→typologie | **0** ❌ |
| Templates lexicaux par typologie | **0** ❌ |
| Tests BE narrative dédiés | 1 (`test_narrative_eur_hero.py`) |
| Tests FE briefing/narrative | 4 |
| Score qualité estimé doctrine §11.3 | **5/10** |

## Verdict

La narrative actuelle est un **MVP fonctionnel** qui sort en 200 ms les bons
chiffres avec sourçage réglementaire correct. Mais elle est **figée dans le
temps** (pas de push +X vs S-1), **figée par typologie** (pas de variation NAF),
**non personnalisée** (vouvoiement générique sans nom de persona) et **ses
acronymes restent bruts** dans le body.

**4/9 cibles doctrine §11.3 atteintes** : longueur adaptée persona ✓,
hiérarchisation 1ère phrase ✓, sourçage réglementaire ✓, signal saillant ✓.
**5/9 cibles manquantes** : 3 typologies, 6 déclencheurs hiérarchisés, push
événementiel, mention persona, variation tonale.

Le sprint d'exécution est **techniquement faisable** (event_bus + naf_resolver
+ weekly_deltas existent déjà — il s'agit d'orchestration, pas de fondations).
Effort estimé **3-5 semaines**.
