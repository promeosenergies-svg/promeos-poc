<!--
PROMEOS Sol — PR template doctrine compliance
Référence narrative : docs/doctrine/doctrine_promeos_sol_v1_1.md (v1.1, 27/04/2026)
Référence exécutable : backend/doctrine/ (constants + kpi_registry + error_codes)
Toute PR significative doit pouvoir être justifiée vis-à-vis de la doctrine.
-->

## Résumé

<!-- 1-3 phrases factuelles. Quoi change, pourquoi, impact périmètre. -->

## Doctrine compliance v1.1 — engineering (§16)

- **Principes respectés** : <!-- numéros, ex: 1, 5, 10, 13 -->
- **Risques ou tensions** : <!-- ex: données partielles sur le site X -->
- **KPIs impactés** : <!-- ex: annual_consumption_mwh, energy_cost_eur — sinon "aucun" -->
- **Sources utilisées** : <!-- Enedis, facture, RegOps, manuel… -->
- **Tests ajoutés** : <!-- unit KPI, integration API, e2e cockpit, source-guard… -->
- **États UX couverts** : <!-- loading, empty, error, partial data — ou "n/a" -->
- **Constantes utilisées** : <!-- import depuis backend/doctrine/constants.py — sinon "aucune" -->

### Critères de rejet engineering (Doctrine §16)

- [ ] Aucun KPI sans fiche dans `backend/doctrine/kpi_registry.py`
- [ ] Aucune règle métier dans le frontend (`tests/doctrine/test_no_frontend_business_logic.py` PASS)
- [ ] Aucune valeur affichée sans unité
- [ ] Aucune route morte introduite
- [ ] Aucune action non reliée à un objet métier
- [ ] Cohérence transverse préservée
- [ ] Aucune donnée incertaine masquée comme certaine
- [ ] `tests/doctrine/` : 20/20 PASS

---

## Doctrine compliance §11.3 — produit/UX (v1.0.1)

> Format obligatoire pour toute PR refonte sol2. Cocher les principes/anti-patterns/tests/personas concernés et justifier en 1 ligne.

### Principes respectés (§3 doctrine)

- [ ] **P1** — Briefing au lieu du dashboard (kicker → Fraunces → narrative → KPIs)
- [ ] **P2** — Navigation comme déambulation guidée
- [ ] **P3** — Grand écart compatible (5 archetypes : tertiaire/industriel/hôtelier/collectivité/mono-site)
- [ ] **P4** — Densité éditoriale (>200px sans info utile = bug)
- [ ] **P5** — Glanceable summary (3 secondes pour comprendre)
- [ ] **P6** — Le produit pousse (chantier α moteur d'événements)
- [ ] **P7** — Le patrimoine vit (J ≠ J+1)
- [ ] **P8** — Simplicité iPhone-grade (apprentissage zéro)
- [ ] **P9** — Chaque brique vaut un produit (standalone)
- [ ] **P10** — Transformer la complexité (acronymes en récit)
- [ ] **P11** — Le bon endroit pour chaque brique (mapping intention → emplacement)
- [ ] **P12** — Sachant et SURTOUT non-sachant

### Principes potentiellement en tension

<!-- Lister les principes que cette PR ne peut pas pleinement servir et pourquoi (ex : "P7 — chantier α non encore livré, à voir Sprint 2"). -->

### Anti-patterns évités (§6)

- [ ] §6.1 visuels — pas de page commençant par tableau/grille KPI sans préambule, pas de card "Aucune action" pleine largeur, palette journal respectée (pas de bleu pétrole/gris ardoise corporate froids), triptyque Fraunces + DM Sans + JetBrains Mono respecté
- [ ] §6.2 navigation — pas de menu 4+ niveaux, pas de sous-page URL-only, pas de route `-legacy` sans plan désactivation
- [ ] §6.3 copy — pas d'acronyme brut en `<h1>`/`<h2>`/titre carte (DT/BACS/APER/OPERAT/TURPE 7/CTA/NEBCO/ARENH/VNU/EUI/DJU/CUSUM/TICGN/aFRR/AOFD), pas de tooltip qui répète l'acronyme sans définir, pas de chiffre sans unité ni source
- [ ] §6.4 produit — pas de feature pour "faire le total", pas de KPI sans définition/source/formule, pas de page identique J vs J+1
- [ ] §6.5 architecture — pas de logique métier frontend (calculs, scoring, formules), pas de source vérité multiple, instrumentation événements présente

### Tests doctrinaux validés (§7)

- [ ] **T1** — 3 secondes (screenshot 3s → résume état immédiatement)
- [ ] **T2** — Dirigeant non-sachant (PME/DAF non-spé comprend essentiel + sait quoi faire en 3min sans aide)
- [ ] **T3** — Grand écart (même page sert ETI 5 sites ET industriel 200 sites)
- [ ] **T4** — Densité (pas plus de 200px sans info utile)
- [ ] **T5** — Standalone (module extrait, vendable seul, suffit à payer abonnement)
- [ ] **T6** — Jour J vs J+1 (1 card/KPI/signal a changé d'état/priorité/contenu)
- [ ] **T7** — Transformation acronymes (phrase principale comprise sans glossaire externe)
- [ ] **T8** — Emplacement (feature trouvée en <2 clics depuis n'importe quelle page)

### Personas servis

- [ ] **Marie** (DAF tertiaire 5 sites, briefing daily 8h45) — note `/10` : <!-- X --> · ce qui marche : <!-- ... --> · ce qui manque : <!-- ... -->
- [ ] **Jean-Marc** (CFO ETI vue COMEX brief CODIR) — note `/10` : <!-- X --> · ce qui marche : <!-- ... --> · ce qui manque : <!-- ... -->
- [ ] **Investisseur** (vision produit, différenciation, multi-archetype démontrable) — note `/10` : <!-- X --> · ce qui marche : <!-- ... --> · ce qui manque : <!-- ... -->

### Constantes inviolables §8.3 touchées (le cas échéant)

<!-- Si la PR modifie/ajoute une constante (CO₂, accise, DT jalon, RegOps poids, NEBCO seuil, OID benchmark, deadline réglementaire), citer la source officielle (Décret/Arrêté/Délib CRE/JORF) + numéro/URL. Sinon : N/A. -->

### Source-guards pytest impactés

<!-- Lister les tests `backend/tests/source_guards/*` qui passent/échouent suite à cette PR. Si nouveau guard nécessaire, le justifier. -->

### Référence ADR / memory

<!-- Lien vers ADR concerné (`docs/adr/ADR-XXX-*.md`) + memory entries pertinents. -->

## Test plan

- [ ] Tests doctrinaux : `pytest tests/doctrine/` → 20/20 PASS
- [ ] Backend : pytest baseline ≥ 6 027 (non-régression)
- [ ] Frontend : vitest baseline ≥ 4 102 + 0 console error
- [ ] Source-guards : tous PASS (`pytest tests/source_guards/`)
- [ ] Tests doctrinaux automatisés (T1/T4/T7) : PASS sur scope PR
- [ ] Playwright captures avant/après (si UI touchée)
- [ ] Lint frontend : `npx eslint` 0 erreur
- [ ] /code-review:code-review et /simplify exécutés (cf workflow obligatoire pre-merge)

## Risque & rollback

<!-- Quel est le pire scénario si cette PR casse la prod ? Rollback en combien de temps ? Feature flag présent ? -->

---

**Doctrine v1.1** — `docs/doctrine/doctrine_promeos_sol_v1_1.md` · executable : `backend/doctrine/`
**Doctrine v1.0.1 (refonte sol2 produit/UX)** — `docs/vision/promeos_sol_doctrine.md`
