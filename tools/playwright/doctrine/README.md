# Tests doctrinaux automatisés — PROMEOS Sol v1.0.1

Référence : `docs/vision/promeos_sol_doctrine.md` §7 — 8 tests doctrinaux.

## Pattern

8 tests Playwright (UI driven) + LLM-eval Claude (jugement non-sachant) qui valident
la doctrine compliance sur le scope refonte sol2. À exécuter en CI à chaque PR
significative et en fin de sprint sur les 7 piliers.

## Les 8 tests

| Test | Quoi | Mécanique | Exécutable Sprint 0bis |
|---|---|---|---|
| T1 — 3 secondes | Screenshot 3s + LLM eval "résume état immédiatement" | Playwright capture + Claude API juge | Pattern, plein S1+ |
| T2 — Dirigeant non-sachant | Persona Marie/Jean-Marc lit page + LLM eval "comprend essentiel + sait quoi faire en 3min" | Playwright + Claude API persona | Pattern, plein S1+ |
| T3 — Grand écart archetype | Pour 5 archetypes seedés, snapshot + assert vocabulaire/benchmarks distincts | Playwright × 5 + regex anti-leak | Plein S3 (chantier β) |
| T4 — Densité (200px sans info) | Mesure pixel par section, assert pas de zone vide >200px | Playwright getBoundingClientRect | ✅ Exécutable maintenant |
| T5 — Standalone | Module extrait, suffit-il à payer abonnement ? Test commercial offline | Manuel + checklist business case | Manuel S6 |
| T6 — Jour J vs J+1 | Snapshot J, mock now() à J+1, assert ≥1 card a changé d'état/priorité | Playwright + backend mock dates | Plein S2 (chantier α) |
| T7 — Transformation acronymes | Grep DOM rendu, aucun acronyme nu en h1/h2/title hors whitelist | Playwright DOM scan + regex | ✅ Exécutable maintenant |
| T8 — Emplacement | Feature trouvée en <2 clics depuis page random | Playwright auto-navigation | ✅ Exécutable maintenant |

## Architecture

```
tools/playwright/doctrine/
├── README.md                    -- ce fichier
├── runner.mjs                   -- orchestre les 8 tests, output JSON+markdown
├── lib/
│   ├── auth.mjs                 -- login JWT helper (réutilise pattern existant)
│   ├── llm_eval.mjs             -- wrapper Claude API pour jugement T1/T2
│   └── pages.mjs                -- liste 8 pages canoniques refonte sol2
├── test_t1_three_seconds.mjs
├── test_t2_non_sachant.mjs
├── test_t3_grand_ecart.mjs
├── test_t4_density.mjs
├── test_t6_day_j_evolution.mjs
├── test_t7_acronyms.mjs
└── test_t8_emplacement.mjs
```

## Usage

```bash
# Exécution complète 8 tests (à élargir sprint après sprint)
node tools/playwright/doctrine/runner.mjs

# Exécution test isolé
node tools/playwright/doctrine/test_t4_density.mjs

# Output : JSON + markdown dans tools/playwright/doctrine/results/{timestamp}/
```

## CI integration

À ajouter dans `.github/workflows/` Sprint 1.1 :
- `doctrine-source-guards.yml` : `pytest backend/tests/test_doctrine_sol_source_guards.py` (déjà disponible)
- `doctrine-tests.yml` : `node tools/playwright/doctrine/runner.mjs` (à activer Sprint 1.1+)

Bloquant en CI à partir Sprint 1.1.

## Statut Sprint 0bis (livré)

- [x] README pattern documenté
- [x] T4 densité — exécutable
- [x] T7 acronymes — exécutable
- [ ] T1/T2 LLM-eval — pattern à activer Sprint 1.1 avec Claude API
- [ ] T3 grand écart — Sprint 3 (chantier β multi-archetype)
- [ ] T5 standalone — manuel S6
- [ ] T6 J vs J+1 — Sprint 2 (chantier α moteur d'événements)
- [ ] T8 emplacement — Sprint 1.1
