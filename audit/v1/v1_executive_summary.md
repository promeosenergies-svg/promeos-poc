# V1 — Executive Summary cartographie statique

**Date**: 2026-04-24 · **Phase**: V1 cartographie read-only · **Livrables**: 4 rapports

## Livrables V1

1. [v1_cartographie_main_front.md](v1_cartographie_main_front.md) — 51 routes MAIN, 6 modules NavRegistry, 60+ pages
2. [v1_cartographie_refonte_sol_front.md](v1_cartographie_refonte_sol_front.md) — 92 routes refonte SOL, 22 pages *Sol, 40+ composants UI Sol
3. [v1_cartographie_backend.md](v1_cartographie_backend.md) — 81 routers, 607 endpoints, 20 services top-size
4. [v1_diff_strategique.md](v1_diff_strategique.md) — 119 commits groupés, 412 fichiers diff, 21/21 pages migrées

## Chiffres clés

| Métrique | MAIN | REFONTE SOL |
|----------|------|-------------|
| Routes front (lazy) | 51 | 62 |
| Routes total (inc. redirects) | 80+ | 92 |
| Pages *Sol | 0 | 22 |
| Composants UI Sol | 0 | 40+ |
| Endpoints backend | 607 | 607 |
| Services backend top-20 | identique | identique |

**Delta refonte vs main** :
- **119 commits** sur 5.7 jours (monoauteur, ~21/jour, structuré P0→P5)
- **+35 636 / -2 950 LOC** = +32 686 net
- **412 fichiers** touchés (318 nouveaux + 94 modifiés)
- **Zéro logique métier backend modifiée** (7 fichiers critiques CLAUDE.md intacts)
- **Seul YAML tarifaire enrichi** (+100 LOC ATRD7 GRDF + biométhane, zéro logique)

## Verdict préliminaire V1

### ✅ Points forts refonte SOL
- Architecture patterns A/B/C claire (6 phases P0→P5)
- 22/22 pages clés migrées
- Tests augmentés : +2500 LOC (source-guards, vitest, a11y)
- A11y hardening P0/P1 complété
- Backend SoT (scoring, unified consumption, emission factors) **intactes**
- 12 bilans + 160 screenshots + 11 audits = traçabilité forte
- Rollback prêt via routes `-legacy` (backward compatible)
- Refonte **mature, pas expérimentale**

### ⚠️ Risques identifiés
| # | Risque | Sévérité |
|---|--------|---------|
| 1 | Routes `-legacy` : 20+ variantes → confusion URL partagées | P1 |
| 2 | `/conformite/dt`, `/bacs`, `/operat` → **404** (onglets futurs) | **P0** |
| 3 | `/audit-sme` route absente (tab ConformiteSol manquante) | P0 |
| 4 | `getCockpit()` null fallback org vide (issue #257) | P0 |
| 5 | CSS index.css +1003 LOC override Tailwind | P1 régression possible |
| 6 | `PurchaseAssistantPage.jsx` dead code non supprimé (main + refonte) | P2 |
| 7 | `Dashboard.jsx` fichier mort jamais routé | P2 |
| 8 | Imports commentés Patrimoine.jsx (5 composants fantômes) | P2 |
| 9 | WCAG P2 non audité complet | P2 |
| 10 | Tests legacy potentiellement oubliés post-migration | P1 |

### ⚠️ Risques backend (communs MAIN+refonte)
- Demo mode overly lenient (`get_optional_auth=None`) — **P0 sécu en prod**
- Soft-delete inconsistency (queries sans `not_deleted()`) — P1
- Compliance score fallback hardcodé 45/30/25 — P1
- 6+ routes deprecated toujours fonctionnelles — P2

## Prochaine étape : V2

**V2 = Audit Playwright live MAIN** (2-3h) :
- Démarrer backend (port 8001) + frontend (port 5173) sur worktree `/Users/amine/projects/promeos-audit-main/`
- Seed HELIOS S
- 27+ routes × 2 personas (tertiaire multisite + industriel agroalimentaire)
- Capture console/network/screenshots
- Rapport `audit_promeos_main_personas_tertaire_industriel.md`

### Questions avant V2

1. **Seed** : je lance `python -m services.demo_seed --pack helios --size S --reset` dans le worktree MAIN ?
2. **Persona data** : HELIOS est tertiaire. Pour persona B agroalimentaire, que faire ?
   - Option A : tester tout de même avec HELIOS en simulant le regard industriel (rapport inclut "crédibilité industrie")
   - Option B : charger MERIDIAN (3 sites) si présent
   - Option C : créer un site agroalimentaire custom (via wizard Sirene ou import)
3. **Captures** : garder les captures Playwright dans worktree ou rapatrier dans `audit/v2/captures/` ?

Je recommande : **1=oui**, **2=option A** (plus rapide, écart crédibilité documentable) + note sur B, **3=audit/v2/captures/** centralisé.
