# Phase 3.4 — Audit UX/UI/CX/CS · Cockpit Jour V2 (commit 0018f45e)

> **STATUS** : Audit rempli le 2026-05-11 par Claude Code sur la base
> de la capture Phase A (commit `17d74366`, 51 PNGs sur 3 viewports).
> Comparaison historique via archives `tools/playwright/captures/` (Phase B
> skipped sur décision user).

---

## Synthèse score

```text
UX  : 12 / 24  (acquis statique)  + 4-6 conditionnel tests user 1.1/1.2
UI  : 23 / 24
CX  : 21 / 24
CS  : 17 / 24
─────────────────────────────────────────
TOTAL ACQUIS         : 73 / 96  (76 %)
TOTAL PROJETÉ        : 79 / 96  (82 %) si tests user 1.1+1.2 ≥ 2/3
SEUIL GO PHASE 3.5   : ≥ 80 / 96
```

**Verdict** : 73-79 / 96, sous le seuil 80. **CRITÈRE BLOQUANT 4.1 à 0**
(HubKpiCard non extrait) → **NO-GO Phase 3.5 automatique** selon la
grille. La correction est l'objet de Phase F.

---

## Méthode

- **0** = absent ou cassé (bloquant, doit être corrigé avant Phase 3.5)
- **1** = présent mais à améliorer
- **2** = correct, conforme à la spec
- **3** = excellent, exemplaire
- **À TESTER** = nécessite intervention humaine (test utilisateur)
- **N/A** = non applicable à l'état actuel

---

## Dimension 1 — UX (User Experience) · 12 / 24

### Compréhension immédiate

| # | Critère | Test | Note /3 | Constat |
|---|---|---|---|---|
| 1.1 | **Test 5s** : DG identifie 3 décisions en 5 secondes | Faire tester 3 personnes hors équipe | **À TESTER** | Personas proposés ci-dessous |
| 1.2 | **Test 30s** : DG explique état parc en 30s | Idem | **À TESTER** | Idem |
| 1.3 | **Hierarchy** : le hero domine clairement | Inspection capture `full-default.png` | **3** | Hero premium-night ~180px haut, fond gradient #072A44→#0B3552, illustration filaire 8 buildings, contraste fort vs corps blanc |
| 1.4 | **Vocabulaire** : aucun acronyme non expliqué | Grep + survol tooltips | **1** | BACS, EMS, OPERAT, CVC, DT apparaissent en hero/highlights sans tooltip. Native `title=` sur KPI 3 uniquement (et pas un Tooltip Sol design). Finding P1. |

#### Personas test 5s + 30s (à solliciter)

| Persona | Profil | Disponibilité |
|---|---|---|
| **DAF d'ETI multi-sites** | DAF d'une ETI tertiaire 8-15 sites IDF/régions, profil Jean-Marc CFO mémoire | Réseau pro 1er cercle Amine |
| **Responsable RH/admin ETI** | RRH ou DAF-adjoint d'une ETI 200-500 employés, exposé à OPERAT/Audit SMÉ | Réseau pro 2nd cercle |
| **Ami DG d'ETI** | DG retail/services 15-30 sites, profil Marie DAF tertiaire mémoire | Réseau direct Amine |

Protocole : ouvrir `/cockpit/jour` headless en plein écran, chronomètre, leur demander :

1. (5s) « Citez les 3 choses qui doivent vous occuper aujourd'hui »
2. (30s) « Expliquez-moi à quoi ressemble votre parc en ce moment »

Note finale 1.1/1.2 = moyenne des 3 réponses scorées 0-3.

### Parcours et navigation

| # | Critère | Test | Note /3 | Constat |
|---|---|---|---|---|
| 1.5 | **Chaque highlight → CTA fonctionnel** | Inspection payload + cliquer 3 CTA | **2** | URLs cohérentes : `/conformite/sites/2/preuve`, `/connectors?site_id=3`, `/conformite/sites/1/bacs`. Routes existantes à confirmer (`/conformite/sites/:id/preuve` non vérifié) — finding P2 si 404. |
| 1.6 | **Pas de cul-de-sac** | Test navigation | **2** | Hero CTA "Voir le centre d'action →" pointe `/anomalies` (existant). Highlights `linkAll` pointe `/anomalies` (Phase 3.0 repoint validé). |
| 1.7 | **Retour cockpit jour fluide** | Test back | **2** | AppShell sidebar persistante, Accueil + tous les hubs visibles. Pas de breadcrumb dédié mais sidebar suffit. |
| 1.8 | **Cross-référence valeurs** | Vérifier KPIs vs /energie | **2** | KPI 1 (16,6 MWh) vient de `consumption_unified_service.get_portfolio_consumption()` = SoT consommation. Cohérent ; à valider live cross-page. |

**Sous-total UX : 12 / 24** (acquis statique, hors tests user 1.1+1.2)

---

## Dimension 2 — UI (User Interface) · 23 / 24

### Fidélité à la maquette v2

| # | Critère | Test | Note /3 | Constat |
|---|---|---|---|---|
| 2.1 | **Hero Premium-night** (#072A44 + illustration filaire) | Comparer `hero-zoom.png` vs maquette V2 | **3** | Rendu pixel-near maquette V2 « juste milieu premium ». Gradient 135deg #072A44→#0B3552 ✓. 8 buildings filaires + 2 anomaly dots chauds ✓. |
| 2.2 | **3 KPI cards icône + valeur Newsreader 38px + delta mono** | Comparer `kpi-1/2/3.png` | **2** | Valeur Fraunces 28px (spec disait Newsreader 38px). PAS d'icône circulaire 42px. Delta mono ✓. **Finding P1** : si Design System Spec attend Newsreader, harmoniser à l'extraction Phase F. |
| 2.3 | **2 graphes côte à côte avec question métier** | Comparer captures full | **3** | « Où la consommation dérive-t-elle ? » + « Sommes-nous proches de la puissance souscrite ? » + answer narratif + chart + footScm. Doctrine §L11.4 respectée. |
| 2.4 | **3 highlights différenciés border-left sévérité** | Comparer `highlight-1/2/3.png` | **3** | P1 crit (rouge terre cuite `--sol-refuse-line`), P2 warn (ambre `--sol-attention-line`), P3 info (gris `--sol-ink-400`). Severity-token-aware ✓. |

### Tokens et palette

| # | Critère | Test | Note /3 | Constat |
|---|---|---|---|---|
| 2.5 | **Aucune couleur hardcodée** dans CockpitJour.jsx | `grep -nE '#[0-9A-Fa-f]{6}'` | **3** | 0 match. Toutes les couleurs via `var(--sol-*)`. |
| 2.6 | **Premium-night uniquement dans hero** | Source guard | **3** | `--sol-night-*` consommé uniquement par `SolHeroPremiumNight`. Pas de fuite vers KPI/charts/highlights. |
| 2.7 | **Triptyque typo Fraunces / DM Sans / JetBrains Mono** | DevTools inspection | **3** | tokens.css définit `--sol-font-display` (Fraunces), `--sol-font-body` (DM Sans), `--sol-font-mono` (JetBrains Mono). Cohérent. |
| 2.8 | **Hairlines fines (0.5px ou 1px)** | DevTools inspection | **3** | `border: 1px solid var(--sol-rule)` partout (ChartFrame, KpiTriptychCard, HubHighlight). Aucune bordure ≥ 2px. |

**Sous-total UI : 23 / 24**

---

## Dimension 3 — CX (Customer Experience) · 21 / 24

### Confiance et crédibilité

| # | Critère | Test | Note /3 | Constat |
|---|---|---|---|---|
| 3.1 | **Footer SCM** présent (Source · Confiance · MAJ · Méthodologie) | Inspection bas de page | **3** | `HubPageFooter` alias `SolPageFooter`. Payload backend fournit 4 sources (EMS, RegOps, ADEME, Bill-Intel) + confidence high + updatedAt ISO + methodologyHref `/methodologie/cockpit-jour`. |
| 3.2 | **Qualité ≠ Confiance séparées** | Inspection meta hero | **3** | Capture montre « QUALITÉ 98 % · CONFIANCE HIGH · SEMAINE 20 · 7 SITES » — séparées. Doctrine §6.4 respectée. |
| 3.3 | **KPI 3 "8 % de la souscrite utilisée"** | Source guard SG_HUB_L11_03 | **3** | Capture KPI 3 : « 121 kW » + delta « +8 % » + sub « de la souscrite utilisée » + footScm « Souscrite 1,5 MW · Marge confortable ». Anti-pattern AP2 (« -92 % vs souscrite » trompeur) corrigé. |
| 3.4 | **Marque PROMEOS orthographe** | Source guard SG_HUB_L11_02 | **3** | 11/11 source-guards verts. Capture login + sidebar PROMEOS uppercase no-accent. |

### Données et traçabilité

| # | Critère | Test | Note /3 | Constat |
|---|---|---|---|---|
| 3.5 | **Chaque KPI** a unité, source, période, qualité, confiance | Inspection payload | **2** | Payload backend fournit tout (unit, source.lastUpdatedAt, period, quality.value, confidence). **Finding P1** : footScm dit « 6 sites » mais hero meta dit « 7 SITES » (cf naming_drift + P0.1 site count : 5 HELIOS + 2 sites Test parasites). Incohérence à traiter Phase E. |
| 3.6 | **Highlights différenciés** (catégories distinctes) | Inspection liste | **3** | Catégories : « Conformité » / « Donnée EMS » / « Conformité BACS » — anti-pattern AP3 (4× même cat) respecté. |
| 3.7 | **Impacts différenciés** (pas 4× "3,8 k€") | Idem | **3** | « 3,8 k€/an » / « — » / « 2027 » : 3 formats distincts (€/an, à confirmer, échéance année). Excellent. |
| 3.8 | **Tooltip aide KPI 3** | Survol KPI 3 | **1** | `title={helpTooltip}` natif browser uniquement — pas un Tooltip Sol design avec arrow + theme. Présent mais expérience dégradée. Finding P1 à traiter Phase F (Tooltip Sol component). |

**Sous-total CX : 21 / 24**

---

## Dimension 4 — CS (Code & System) · 17 / 24

### Architecture composants

| # | Critère | Test | Note /3 | Constat |
|---|---|---|---|---|
| 4.1 | **`<HubKpiCard>` extrait** dans `grammar/hub/` | Inspection imports CockpitJour.jsx | **0 ← BLOQUANT** | `KpiTriptychCard` est inline dans `pages/CockpitJour.jsx` (lignes 41-168). Pas d'import depuis `components/grammar/hub/HubKpiCard`. **Bloquant Phase 3.5** : 5 hubs recopieraient chacun leur propre composant inline (drift garanti). Décision Phase E : GO extraction Phase F. |
| 4.2 | **Page CockpitJour.jsx = composition pure** | Lecture (`< 200 lignes` attendu) | **1** | **560 lignes** (vs ≤200 ciblé). Contient : KpiTriptychCard (~130) + BarsDaily7d (~50) + LineCharge24h (~80) + CockpitJourSkeleton (~40) + ErrorBlock (~50) + page (~150). 5 helpers locaux à extraire. Cible post-Phase F : ~170 lignes. |
| 4.3 | **5 primitifs L11** utilisés | Grep imports | **3** | `HubPage`, `SolHeroPremiumNight`, `ChartFrame`, `HubHighlight`, `HubPageFooter` importés depuis `components/grammar`. SG_HUB_L11_01 vert. |
| 4.4 | **Aucun composant ad-hoc** | Inspection | **1** | 5 composants locaux : `KpiTriptychCard`, `BarsDaily7d`, `LineCharge24h`, `CockpitJourSkeleton`, `ErrorBlock`. Aucun import externe ad-hoc (pas de violation source-guard), mais 5 fonctions JSX qui mériteraient grammar/hub/ ou ui/sol/. Note 1 = présent et utile mais non extrait. |

### Tests et CI

| # | Critère | Test | Note /3 | Constat |
|---|---|---|---|---|
| 4.5 | **11 source-guards Vitest** verts | `npm run test cockpit_jour_l11` | **3** | 11/11 verts (SG_HUB_L11_01 5/5 + SG_HUB_L11_02 2/2 + SG_HUB_L11_03 2/2 + structure 2/2). |
| 4.6 | **23 tests backend** verts | `pytest test_cockpit_jour_endpoint.py` | **3** | 23/23 verts (commit d93eb652). |
| 4.7 | **Vitest baseline 4 680** | `npm run test` | **3** | Confirmé 4 678 passed + 2 skipped = 4 680 total (vs 4 669 avant Step 6, +11). |
| 4.8 | **Playwright snapshots baseline OK** | Capture Phase A | **3** | 51 PNGs Phase A. **Limitation** : `?demo_state=*` non implémenté → loading/empty/error/partial rendent identique à default (à activer Phase E ou Phase F). À noter mais pas bloquant pour le critère 4.8 stricto sensu. |

**Sous-total CS : 17 / 24**

---

## Total et décision

```text
UX  : 12 / 24  (acquis ; +4-6 conditionnel tests user 1.1/1.2)
UI  : 23 / 24
CX  : 21 / 24
CS  : 17 / 24
─────────────────────────────────────────
TOTAL ACQUIS  : 73 / 96  (76 %)
TOTAL CIBLE   : 79 / 96  (82 %) si tests user 1.1+1.2 ≥ 2/3
SEUIL GO Phase 3.5 : ≥ 80 / 96 + 0 critère à 0
```

### Décision Phase 3.5

| Critère décisionnel | Statut |
|---|---|
| Score total | **76-82 %** (zone NO-GO ou CORRECTION) |
| Critères à 0 | **1 (4.1 HubKpiCard inline)** → **NO-GO automatique** |
| Critères à 1 | 4 (1.4 acronymes, 4.2 lignes page, 4.4 ad-hoc, 3.8 tooltip) |

### Bloquants identifiés (à traiter avant scaling)

| # | Critère | Sévérité | Phase fix |
|---|---|---|---|
| **4.1** | `HubKpiCard` non extrait | **BLOQUANT P0** | **Phase F** (extraction) |
| 4.4 | 5 composants locaux non factorisés | P1 | Phase F (extraction graduelle) |
| 4.2 | Page 560 lignes (vs ≤ 200 cible) | P1 | Phase F (suite extraction) |
| 1.4 | Acronymes BACS/EMS/OPERAT/CVC/DT sans tooltip Sol | P1 | Phase F (Tooltip Sol component) |
| 3.8 | Tooltip native HTML sur KPI 3, pas Tooltip Sol | P1 | Phase F (idem) |
| 3.5 | Footer SCM dit « 6 sites » vs hero « 7 sites » | P1 | Backend `_build_cockpit_jour_kpis` + `_build_cockpit_jour_hero` cohérent + fix is_demo filter (cf naming_drift P0.1) |
| 2.2 | KPI valeur Fraunces 28px vs Newsreader 38px spec | P2 | Phase F |
| 1.5 | URLs CTA highlights non testées (404 possible) | P2 | Phase D-bis cliquage live |
| 4.8 | `?demo_state=*` non implémenté | P2 | Phase E (impl. ou abandon) |

### Findings P0 confirmés par cet audit

- **4.1 BLOQUANT** : HubKpiCard non extrait → décision Phase E doit être GO extraction.
- **3.5 P1 critique** : la fuite cross-tenant cosmétique (« 7 sites » incluant 2 sites Test parasites) doit être documentée et traitée Phase F (filtre `is_demo=True` côté `_sites_for_org`).

### Personas à solliciter (1.1 + 1.2)

3 profils proposés ci-dessus (Dimension 1). Score réaliste anticipé :

- Si rendu V2 est aussi clair que la maquette suggère → 2/3 sur tests = +4 points
- Si maquette V2 trop verbeuse pour DG non-énergie → 1/3 = +2 points
- Worst case : 0/3 = +0 points (UX = 12/24, plafond TOTAL 73/96)

**Avec extraction Phase F + correction des 4 P1 du tableau** :

- 4.1 passe 0 → 3 (extraction) = +3
- 4.4 passe 1 → 3 (factorisé) = +2
- 4.2 passe 1 → 3 (~170 lignes) = +2
- 1.4 + 3.8 passent 1 → 2 (Tooltip Sol) = +2
- 3.5 passe 2 → 3 (filtre is_demo) = +1

**Projection post-Phase F** : 73 + 10 = **83/96** (87 %) → **GO Phase 3.5 acquis**.

---

## Prochaine étape

**STOP — validation user requise avant lancer Phase E (décision GO/NO-GO HubKpiCard)**.

L'audit confirme la recommandation forte du fichier
`phase_3_4_decision_hubkpicard.md` : **GO extraction Phase F maintenant**
plutôt qu'après Phase 3.5 (ROI ×3).
