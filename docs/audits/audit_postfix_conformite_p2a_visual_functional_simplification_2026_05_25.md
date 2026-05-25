# Audit postfix — Conformité P2-A simplification visuelle (2026-05-25)

**Branche** : `claude/conformite-p2a-visual-functional-simplification`
**Base** : `claude/hotfix-conformite-framework-labels` (qui inclut hotfix #301 et tous les merges récents #296-#300)
**Verdict** : 🟢 **GO — 14/14 contrôles Playwright verts**

## Contexte du sprint

Captures utilisateur (avant fix) : `/conformite` longue + anxiogène. Bugs visibles :
- 3 lignes APER (corrigé par hotfix #301)
- Score 36/100 répété en plusieurs endroits
- Pénalité **0 €** dans le score / **45 k€** dans la frise → contradiction DAF
- Périmètre ambigu (5 sites ici, 13 sites là)
- Beaucoup de scroll, blocs experts dépliés par défaut
- Textes anxiogènes ("Données limitées", "À réaliser" sans accent)

## Diagnostic Phase 0 (READ-ONLY)

| Divergence | Source | Sévérité | Fix livré |
|---|---|---|---|
| **5 sites vs 13 sites** | `scopedSites.length` (scope user) ≠ `bundle.summary.total_sites` (org complète) — **pas un bug, 2 périmètres distincts** | UX | Label « X sites évalués sur Y dans le périmètre » dans la synthèse compacte |
| **0 € vs 45 k€** | `score.total_impact_eur` **hardcodé à 0** dans `ConformitePage.jsx:367` alors que `/api/compliance/timeline.total_penalty_exposure_eur` exposait la vraie valeur (SoT backend) | 🔴 P0 | Suppression hardcode + consommation `timeline.total_penalty_exposure_eur` |
| **J-128 vs J-139** | Plusieurs deadlines (1 par obligation), légitime — manquait juste une « Prochaine échéance » unifiée | UX | Carte « Prochaine échéance » dans la synthèse compacte (date + jours + obligation) |
| **APER × 3** | Déjà fixé par hotfix #301 | ✅ Résolu | Vérification anti-régression dans audit (1 fois max) |

## Chantiers livrés

### Phase 1 — Fixes P0 crédibilité

1. **Labels frameworks** : déjà livré par hotfix #301 (label_fr backend, formatFrameworkCode fallback neutre, jamais "APER"). Vérification anti-régression : APER apparaît 1 fois max (test source-guard + Playwright).

2. **Cohérence sites** : `ConformiteSyntheseCompacte` rend explicitement le libellé périmètre :
   - Si scope ≠ total : « **5 sites évalués sur 13** dans le périmètre »
   - Si scope = total : « **13 sites** dans le périmètre »
   - Si périmètre = 0 : label masqué (anti-erreur 0/0)

3. **Cohérence pénalité** :
   - **Avant** : `total_impact_eur: 0` (placeholder dur dans le frontend) → DAF voyait 0 € en haut et 45 k€ en bas.
   - **Après** : `total_impact_eur = timeline.total_penalty_exposure_eur ?? null` (SoT backend canonique).
   - Si valeur calculée : montant formaté FR (« 16 500 € »).
   - Si non calculable : libellé « **à qualifier** » (tooltip `<Explain term="penalty_exposure">`).
   - **Plus jamais de « 0 € » trompeur affiché.**

4. **Prochaine échéance unifiée** : carte 2 de la synthèse compacte affiche :
   - Date FR (« 30 septembre 2026 »)
   - Jours restants (« dans 128 jours »)
   - Libellé obligation (« OPERAT 2025 »)
   - Source : `/api/compliance/timeline.next_deadline` (SoT canonique).
   - Fallback : « Aucune échéance proche dans les 12 mois ».

### Phase 2 — Simplification UI (4 zones)

Refonte de la page `/conformite` **sans créer de nouvel écran** :

#### Zone 1 — Synthèse compacte (above-the-fold, 4 cartes max)

[`ConformiteSyntheseCompacte.jsx`](../../frontend/src/components/conformite/ConformiteSyntheseCompacte.jsx) rend en grid (1/2/4 cols responsive) :

| # | Carte | Source données | Couleur seuil |
|---|---|---|---|
| 1 | **Score conformité** | `complianceScore.score` (SoT BE) + subtitle actionnable | rouge<50, ambre 50-69, émeraude ≥70 |
| 2 | **Prochaine échéance** | `timeline.next_deadline` (date + jours + label) | neutre |
| 3 | **Actions prioritaires** | `actionableFindings.length` + CTA « Voir le plan » → tab execution | neutre |
| 4 | **Preuves manquantes** | obligations sans preuve déposée + risque financier (SoT BE) + CTA « Compléter » | neutre |

Le DAF / DG ont l'information critique en **30 secondes** sans scroll.

#### Zone 2 — Priorités (existant préservé)

`ComplianceSummaryBanner` (top 3 urgences) + `GuidedModeBandeau` + `NextBestActionCard` restent visibles sous la synthèse — pas touchés ce sprint pour limiter le diff.

#### Zone 3 — Obligations (chips réglementaires + tabs)

Chips réglementaires (Vue d'ensemble · DT · BACS · APER · SMÉ/BEGES) et tabs (Obligations · Données · Plan · Preuves) restent inchangés — déjà conformes au design after PR #300.

#### Zone 4 — Détails experts repliés par défaut

Wrappés dans `<details>` HTML natif (a11y) :
- **« Contexte éditorial et fraîcheur des données »** : `SolBriefingHead` + freshness + DevBadges + `HealthSummary` (expert) + `CrossModuleCTA` (achat énergie)
- **« Frise réglementaire complète (N échéances) »** : `RegulatoryTimeline` complet (anti-anxiogène, le DAF a déjà la prochaine échéance dans la carte 2)

Les personas experts (Auditeur, RegOps, Customer Success) gardent l'accès au contenu intégral en 1 clic.

### Phase 3 — Micro-copy

| Avant | Après |
|---|---|
| `CONFIDENCE_DATA_LABELS.medium = 'Données partielles'` | « **Données partielles — score à fiabiliser** » |
| `CONFIDENCE_DATA_LABELS.low = 'Données limitées'` | « **Données à compléter pour fiabiliser le score** » |
| `AuditSmeCard A_REALISER = 'A realiser'` (sans accent) | « **Action requise** » |
| `AuditSmeCard NON_CONCERNE = 'Non concerne'` | « **Non concerné** » (accent ajouté) |
| `AuditSmeCard NON_DETERMINE = 'Non determine'` | « **Non déterminé** » (accent ajouté) |

Subtitle du score (carte 1) :
- Si pct < 50 : « Score faible — **N actions prioritaires** à traiter »
- Si 50 ≤ pct < 70 : « Score moyen — quelques obligations à fiabiliser »
- Si pct ≥ 70 : « Score satisfaisant — maintenir le suivi »
- Si pct null : « **Données à compléter pour fiabiliser le score** »

### Phase 4 — Tests

**30 nouveaux tests verts** :

| Suite | Couverture | Tests |
|---|---|---|
| Source-guard `conformite_p2a_simplification.test.js` (NEW) | Anti-régression hardcode `total_impact_eur: 0` + 4 cartes ATF + repli `<details>` + anti texte anglais + anti « KB » visible + accents | **13 ✅** |
| Render jsdom `ConformiteSyntheseCompacte.test.jsx` (NEW) | Score seuil couleur + périmètre divergent/aligné + CTAs conditionnels + risque "à qualifier" vs montant formaté + Prochaine échéance fallback | **17 ✅** |
| **Non-régression** | Suite `src/` complète : 4752 ✓ / 521 fails **tous pré-existants** (baseline pré-P2A identique à 5 tests près en notre faveur) | **0 régression** |

### Phase 5 — Audit postfix Playwright

Script [`scripts/audit_postfix_conformite_p2a.mjs`](../../scripts/audit_postfix_conformite_p2a.mjs) — **14/14 verts** sur `/conformite` en mode démo HELIOS :

```
✅ 1. /conformite HTTP 200
✅ 2. Synthèse compacte ATF visible (above-the-fold)
✅ 2.score Carte score rendue
✅ 2.echeance Carte echeance rendue
✅ 2.actions Carte actions rendue
✅ 2.preuves Carte preuves rendue
✅ 3. Libellé périmètre clair : "5 sites dans le périmètre"
✅ 4. Risque financier rendu : "Risque financier : 16 500 €"
✅ 5. Frise réglementaire repliée par défaut (visible: true, open: false)
✅ 6. Briefing éditorial replié par défaut (open: false)
✅ 7. RiskBadge dupliqué retiré (data-testid="conformite-risk-badge" absent)
✅ 8. APER apparaît 1 fois (max 1 attendu)
✅ 9. 0 console error bloquant (0 / 0 total)
✅ 10. 0 network 5xx bloquant (0 / 0 total)
```

**Découverte clé** : le portfolio HELIOS expose maintenant un risque réel **16 500 €** (sourcé `timeline.total_penalty_exposure_eur`) — exit le « 0 € » trompeur.

## Critères d'acceptation (10/10 ✅)

| # | Critère | État |
|---|---|---|
| 1 | Page lisible sans peur en 30 secondes | ✅ 4 cartes ATF avec libellés actionnables |
| 2 | Above-the-fold = 4 messages maximum | ✅ Synthèse compacte = 4 cartes exactement |
| 3 | APER n'est plus répété à tort | ✅ 1 occurrence max (vérifié Playwright) |
| 4 | 5 sites / 13 sites clarifié | ✅ Libellé « X évalués sur Y dans le périmètre » |
| 5 | Pénalité unique et sourcée | ✅ `timeline.total_penalty_exposure_eur` (SoT BE) ou « à qualifier » |
| 6 | Frise et règles repliées par défaut | ✅ `<details>` HTML natif, `open: false` |
| 7 | Chaque obligation a un CTA principal clair | ✅ CTAs uniques par carte (« Voir le plan », « Compléter ») |
| 8 | Aucun nouveau menu | ✅ Composition pure dans la page existante |
| 9 | Aucun écran fantôme | ✅ Aucune route ajoutée |
| 10 | Tests verts + audit livré | ✅ 30 nouveaux verts + 14/14 Playwright + doc |

## Doctrine respectée

- ✅ **§6.2 hub unique** : `/conformite` reste l'entrée unique, aucun nouveau menu
- ✅ **§8.1 zero business logic frontend** : la pénalité vient de `timeline.total_penalty_exposure_eur` (BE), le label de chaque framework vient de `fw.label_fr` (BE)
- ✅ **Aucun fallback métier faux** : `formatFrameworkCode` est purement présentation, jamais "APER" hardcodé
- ✅ **Français clair + accents** : « Non concerné », « Non déterminé », « Action requise »
- ✅ **Aucun jargon non expliqué** : `<Explain term="penalty_exposure">à qualifier</Explain>` pour la pénalité non calculée
- ✅ **Aucun ACC / PMO / Flex / Partner Hub** introduit

## Dette restante P1/P2 (hors scope sprint)

### P1 — Backend consolidation
- **Pénalité unifiée backend** : actuellement, `timeline.total_penalty_exposure_eur` somme les `event.penalty_eur` du timeline. Idéalement, créer un service `penalty_exposure_service.py` ou ajouter `total_penalty_exposure_eur` au payload `/api/compliance/portfolio/score` (cohérence avec autres KPIs unifiés).
- **Dual engine consistency** : `compliance_rules.py` (legacy YAML) vs `regops/engine.py` (RegAssessment SoT) peuvent diverger. À consolider via 1 seul moteur (sprint dédié RegOps).
- **Endpoint alias dupliqué** : `/api/compliance/sites/{id}/score` + `/api/compliance/site/{id}/score` — dépublier un.

### P2 — Frontend polish
- **Cartes obligations repliables** : Zone 3 actuelle (ObligationsTab) est déjà des cartes mais ne sont pas `<details>`. À transformer pour cohérence ATF.
- **Renommage « Règles détectées automatiquement »** : la section « Obligations détectées par la KB » (si encore visible dans `ObligationsTab`) à renommer.
- **`fetch()` natif** : ConformitePage utilise `fetch()` natif lignes 237-239 au lieu de `api` service (incohérent avec les autres appels). À harmoniser.
- **CEE acronyme** : ligne 966 affiche "Certificats d'Économies d'Énergie (CEE)" sans wrapper `<Explain>` interactif.
- **Tests render hotfix #301 cassés sur cette branche** : le test `ComplianceScoreHeader_framework_labels.test.jsx` qui passait sur la branche hotfix échoue maintenant avec `ReferenceError: React is not defined` — c'est pré-existant à mon sprint (vérifié avec `git stash`). À investiguer (probablement lié au JSX runtime config Vite).

## Verdict

🟢 **GO** — les 4 P0 du brief sont corrigés (labels, sites, pénalité, échéance), la page est lisible en 30 secondes (4 cartes ATF), les détails experts sont repliés par défaut, et les 14 contrôles Playwright passent. Aucun nouveau menu, aucun écran fantôme, doctrine §6.2 + §8.1 respectées.
