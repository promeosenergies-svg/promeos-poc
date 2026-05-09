# Synthèse exécutive — Sprint Grammaire Produit v1 — Phase 0

_Capturé 2026-05-09 · branche `claude/refonte-sol2` · 8 vues × 3 viewports × 2 modes = 48 screenshots · 3 agents general-purpose en parallèle · doctrine référence : `docs/vision/promeos_sol_doctrine.md` v1.1 + ADR-001._

## Verdict global

**Score doctrinal moyen : 5,1 / 10** (cible : 8,5+).
Les fondations Sol sont posées (triptyque typo Fraunces / DM Sans / JetBrains Mono · palette journal · navigation rationalisée) mais la **grammaire éditoriale §5** et la **transformation des acronymes (§6.3)** n'ont jamais été industrialisées de manière transverse. Les violations sont massivement systémiques, non locales : un effort transverse sur 4-5 primitifs débloque la moitié de la dette.

| Vue (8) | Score | P0 | P1 | P2 | Verdict |
|---|---|---|---|---|---|
| Anomalies | 7,5 | 0 | 1 | 2 | **Référence Sol** — la mieux alignée |
| Conformité | 7,0 | 1 | 1 | 1 | Excellente sauf L4 (acronymes) |
| Factures (Bill-Intel) | 6,0 | 2 | 1 | 1 | Bon mais L4 + L6 bloquants |
| Cockpit Stratégique | 5,5 | 2 | 0 | 3 | Éditorial abouti, manque source/tooltip |
| Cockpit Jour | 5,0 | 1 | 3 | 1 | Palette OK, narrative absente |
| Site360 Paris | 5,0 | 1 | 3 | 2 | Drill-down OK, 9 KPIs above-fold |
| Centre d'action | 3,0 | 4 | 2 | 2 | Journal brut, anti-pattern frontal |
| **Onboarding** | **1,5** | **5** | **2** | **0** | **Mismatch URL/contenu — affiche Cockpit Stratégique** |

---

## Top 5 violations transverses (P0 + P1 cumulés)

| # | Loi | P0 / P1 | Vues touchées | Diagnostic |
|---|---|---|---|---|
| 1 | **L6 — Footer SCM** (Source · Confiance · Mis à jour, §5) | 4 / 4 | **8 / 8** | Aucune vue n'expose le `SolPageFooter` doctrinal. Crédibilité B2B non servie. **Violation 100 %.** |
| 2 | **L4 — Acronymes transformés** (anti-pattern §6.3) | 4 / 1 | 6 / 8 | TURPE / CSPE / TICFE / CTA / DT / BACS / APER / ARENH / OPERAT / GISMO / CTC servis bruts. Bloque le test 2 doctrinal (dirigeant non-sachant). |
| 3 | **L3 — KPIs ≤ 3 + tooltip + source** (§5 + §6.4) | 3 / 2 | 7 / 8 | Le glyphe `?` tooltip et l'attribution de source manquent presque partout. Le count `≤3` est respecté sauf Site360 (9 KPIs). |
| 4 | **L1 — Hero préambule** (anti-pattern §6.1) | 3 / 1 | 5 / 8 | Plusieurs pages s'ouvrent sur grille KPI sans préambule (centre-action, site360, onboarding, cockpit-jour partiel). |
| 5 | **L9 — Le produit pousse, ne tire pas** (principe 6) | 2 / 2 | 7 / 8 | Listes plates non hiérarchisées (centre-action 8 items, cockpit événements sans rang). |

> Lois respectées : **L2 _Triptyque typo_** (8 / 8) et — sous l'angle "count ≤ 3" — **L3 partiel** (7 / 8). Acquis Sprint 1 doctrine consolidé.

---

## Top 5 quick wins (gain maximal / effort minimal)

| # | Quick win | Élimine | Effort | Gain |
|---|---|---|---|---|
| 1 | **`SolPageFooter`** primitif universel (Source · Confiance · Mis à jour) déployé sur les 8 vues | L6 sur 8 / 8 vues | 1-2 j-h | Crédibilité B2B + fin de la violation #1 transverse |
| 2 | **`KPISource`** : enrichir `KPIDescriptor` avec tooltip `?` obligatoire + slot footer source | L3 sur 7 / 8 vues | 2-3 j-h | Source de vérité unique côté frontend, déjà conforme à doctrine §8 (zero calcul FE) |
| 3 | **`AcronymeDef`** + dictionnaire `acronymes_doctrine.yaml` (~40 termes) consommé via `<Term />` qui transforme TURPE / DT / BACS en récit-tooltip | L4 sur 6 vues | 3-5 j-h | Test 2 doctrinal franchi (dirigeant non-sachant) |
| 4 | **Retrait ou redirect `/onboarding`** vers `/cockpit/jour` en attendant un vrai wizard | L1 + L8 + L9 + L11 P0 (5 violations) sur 1 vue | 30 min | Élimine la pire vue du repo (1,5 / 10) en moins d'1 h |
| 5 | **`ActionPriorityCard`** week-card typée (À regarder / À faire / Bonne nouvelle / Dérive) déployée sur Centre d'action + Cockpits | L1 + L7 + L9 P0 sur 2-3 vues | 3-5 j-h | Active le principe cardinal 6 (le produit pousse) — actuellement absent du repo |

**Effort total quick wins : ~10-15 j-h pour faire passer le score moyen de 5,1 à ~7,0 / 10.**

---

## Recommandation Phase 1 — primitifs à industrialiser

L'audit montre que **4 templates suffisent** pour absorber 80 % des violations. Le sprint Phase 1 doit créer ces primitifs **avant tout déploiement vue par vue** :

1. **`<SolPageFooter />`** — règle L6 (100 % violations). Contrat : `source`, `confiance` (entier 0-100 %), `updatedAt` (datetime backend). Doctrine §5 + §6.4 explicites.
2. **`<KPISol />`** — wraps `KPIDescriptor` existant + tooltip `?` + slot source obligatoire. Lint anti-régression : KPI rendu sans source = build fail (déjà philosophie ADR-016).
3. **`<Term acronyme="TURPE 7" />`** — consomme `acronymes_doctrine.yaml`. Réécrit acronyme inline en récit + tooltip détaillé. Active test 2 doctrinal partout d'un coup.
4. **`<SolHero kicker="..." titre="..." narrative={...} />`** — primitif éditorial qui code la séquence Kicker > Titre Fraunces > Narrative chiffrée 2-3 lignes. Manque sur cockpit-jour, site360, centre-action, onboarding.
5. **`<WeekCard variant="a-regarder | a-faire | bonne-nouvelle | derive" />`** — opérationnalise principe 6 (le produit pousse). Manque sur centre-action et cockpits.

**Phase 2 (déploiement)** : application des 5 primitifs sur les 8 vues, vue par vue, avec source-guard pre-commit `no-bare-acronym`, `no-kpi-without-source`, `no-page-without-footer`. Approche cohérente avec ADR-016 (enforcement runtime) déjà en place.

---

## Estimation effort révisée

| Lot | Description | Effort |
|---|---|---|
| **Phase 1 — primitifs** | 5 composants (`SolPageFooter`, `KPISol`, `Term`, `SolHero`, `WeekCard`) + dictionnaire acronymes | **8-12 j-h** |
| **Phase 2 — déploiement transverse** | 8 vues × ~2 h refacto = appliquer les primitifs + tests Vitest + Playwright snapshot | **10-15 j-h** |
| **Phase 3 — source-guards** | 3 lints pre-commit + 3 tests pytest doctrine | **2-3 j-h** |
| **Phase 4 — onboarding réel** | Retirer redirect, implémenter vrai wizard premier pas (test 2 doctrinal) | **5-8 j-h** |
| **Phase 5 — site360 refacto** | Réduire 9 KPIs above-fold à 3 + ajout hero | **3-5 j-h** |
| **Total révisé** | | **28-43 j-h** |

> L'estimation initiale du prompt n'est pas connue. Le périmètre Phase 0 + Phase 1 + Phase 2 (les 3 livrables de cette synthèse) se cale dans **15-25 j-h** si on exclut Phase 4 (onboarding réel) et Phase 5 (site360 refacto), qui peuvent partir en sprint dédié.

---

## Recommandations méthodologiques pour Phase 1+

1. **Brancher les source-guards _avant_ le déploiement** : le repo a déjà l'infrastructure (ADR-016 enforcement, source-guards pytest). Reprendre le même pattern pour grammar = anti-régression durable.
2. **Vue de référence = `/anomalies`** (7,5 / 10) : c'est la grammaire Sol la plus aboutie du repo. Tous les primitifs Phase 1 doivent **d'abord** être validés sur Anomalies, puis appliqués aux 7 autres vues. Ne pas réinventer ce qui est déjà bon.
3. **`/onboarding` = quick win immédiat hors Phase 1** : 30 min de redirect technique débloque la pire vue du repo. À traiter dans le commit Phase 0 lui-même si Amine est OK.
4. **L'audit actuel n'a pas mesuré : `red_surface_ratio` pixel-précis, font-sizes-count CSS-précis** — les agents ont estimé visuellement. Si Phase 1 nécessite des seuils chiffrés stricts (ex : ≤ 7 font-sizes), prévoir un script d'introspection CSS Playwright en complément (~1 j-h).

---

## 🛑 HARD STOP — Ne PAS continuer Phase 1 sans validation Amine

**Output attendu :** "OK Phase 0, go Phase 1" ou "Stop, ajuster X".

Points spécifiques sur lesquels arbitrage demandé :

- **Q1.** OK pour les **5 primitifs** Phase 1 listés ? Ou ajout/retrait ?
- **Q2.** OK pour le **redirect immédiat de `/onboarding` → `/cockpit/jour`** (quick win 30 min) **avant** Phase 1 ?
- **Q3.** Le mapping `/centre-action` → `/?actionCenter=open&tab=actions` et `/factures` → `/bill-intel` reflète bien l'intention produit ? Ou faut-il créer de vraies routes alias ?
- **Q4.** Le Site360 (9 KPIs above-fold) sort de Phase 1 (sprint dédié Phase 5) ou doit être inclus ?
- **Q5.** Le site `id=1` (entier) au lieu de slug `site_paris_bureaux` pose-t-il un problème produit ? URL pas SEO-friendly, pas mémorisable. À traiter dans un sprint patrimoine ?

---

_Artefacts livrés Phase 0 :_

- `docs/audits/grammar_v1/screenshots/{slug}/{viewport}-{mode}.png` (48 PNG)
- `docs/audits/grammar_v1/index.html` — review humain side-by-side
- `docs/audits/grammar_v1/findings/*.md` (8 fichiers YAML structurés)
- `docs/audits/grammar_v1/violation_matrix.md` (10 × 8 + classements)
- `docs/audits/grammar_v1/SYNTHESE_AUDIT_PHASE_0.md` (ce document)
- `docs/audits/grammar_v1/capture_report.json` (metadata + erreurs réseau)
- `docs/audits/grammar_v1/violations.json` (parse structuré pour automatisation)
- `tools/playwright/grammar_audit_v1.mjs` (script reproductible — `node tools/playwright/grammar_audit_v1.mjs`)
