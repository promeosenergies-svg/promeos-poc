# Phase 3.4 candidate — Application doctrinale L11 Hub Page

_Capturé 2026-05-09 fin de session · branche `claude/refonte-sol2` · Sprint Grammaire v1 → v1.2 (addendum L11)._

## Contexte

Le user a livré 2 artefacts cardinaux :

1. **Capture mockup** « Proposition A · Briefing journal calme » (score auto-évalué 9,2/10) — `cockpit/jour` reconstruite avec **5 lignes de file diversifiées 1 par pilier** (P1 CONFORMITÉ + P2 INVESTISSEMENT + P3 ACHAT + P4 ANOMALIE + P5 ACTION), chacune avec verbe d'invitation propre.
2. **Addendum doctrinal** `sol_v1_1_addendum_hub_page.md` qui ajoute la **Loi L11 Hub Page** aux 10 lois existantes Sol v1.1.

L'addendum a été ingéré dans `docs/vision/promeos_sol_doctrine.md` v1.1 (sections 12.1 → 12.9, ce commit).

## Audit Proposition A — résultats

### Conformité doctrinale

| Loi | Cible | Mesure Proposition A | Verdict |
|---|---|---|---|
| **L11.1** 3 KPIs sémantiques | 3 KPIs canoniques pilier | 3 angles temporels (mois 16,6 MWh / J-1 5,0 MWh / pic 121 kW) | **PASS** |
| **L11.2** 2 graphes domaine | 2 graphes Q→R | Conso 7j + Courbe charge J-1 | **PASS** |
| **L11.3** 3-5 highlights + invitation | 3-5 lignes verbe obligatoire | 5 lignes P1-P5, verbes : voir preuve / lancer / comparer / auditer / voir détail | **PASS** |
| **L11.4** anti-surcharge | Pas de tableau >5×6 | Aucun tableau | **PASS** |
| **L11.5** structure répétable | Composition identique cross-piliers | Gabarit reproductible | **PASS** (à valider sur 4 hubs restants) |

**Conformité L11 : 5/5 ✅** — Proposition A est la **référence canonique** du pattern Hub Page.

### Audit personas

| Persona | Score | Forces | Frictions résiduelles |
|---|---|---|---|
| **Marie DAF non-sachante** | **8,8/10** | Test 3s PASS · Tonalité calme · 5 enjeux différents | « BACS » / « ARENH » / « EMS » / « post-ARENH » bruts |
| **Jean-Marc CFO** | **9,3/10** | 5 priorités chiffrées € · Catégories explicites · Footer SCM | P5 « — » d'impact (transparent mais cardinal CFO veut un proxy) · 2 scénarios sans écart € pré-arbitré |
| **Sophie VC démo 5 min** | **9,5/10** | Premium journal · 5 piliers cross-stream · 0% rouge above-fold | Score dev visible à retirer pour démo client · CTA « Lancer démarche complète » manquant |
| **Energy Manager 30s** | **8,9/10** | Triptyque KPI temporel direct · 2 outils monitoring quotidiens · « Voir preuve opérationnelle » langage technique attendu | Redondance KPI3 footer ↔ P5 ligne file |

**Score consolidé : 9,1/10** (cohérent avec auto-évaluation 9,2/10).

### Anti-patterns L11 — vérification 10/10

0 anti-pattern détecté ✅

## Gap analysis vs Phase 3.2 livré (`60649e33` cockpit/jour)

| Critère | Phase 3.2 livré | Proposition A | Action Phase 3.4 |
|---|---|---|---|
| **Top 3 décisions** | 1 DEC agrégée FE (5 sites — une revue conformité) | **5 lignes diversifiées 1 par pilier** | **Backend** : diversifier `/api/cockpit/priorities` cross-pillar Pareto |
| **Format DEC** | DecisionEvidenceCard verticale 4 cells | Ligne plate compacte + verbe d'invitation | **FE** : créer `<HubHighlight />` (compact) en complément de `<DecisionEvidenceCard />` |
| **Anti carbone-copy** | Solution FE (agrégation typologie) | Solution BE (1 priorité par typologie) | Architecturalement supérieur côté BE |
| **Grammaire L11** | Approximation (DEC top 3) | Référence canonique L11 | Migrer DEC top 3 → HubHighlight |

## Plan d'application Phase 3.4 — 6 priorités

### Priorité 1 — Backend diversification (~1 j-h)

`backend/routes/cockpit.py:get_cockpit_priorities` :
- Forcer **1 priorité par typologie** (CONFORMITÉ / INVESTISSEMENT / ACHAT / ANOMALIE / ACTION)
- Si typologie absente, fallback "—" d'impact (cohérent P5 mockup)
- Tri Pareto cross-pillar (pas same-typology repeat)

### Priorité 2 — Composant `<HubPage />` + `<HubHighlight />` primitif (~2 j-h)

```jsx
<HubPage
  pillar="briefing"
  context={{ kicker, titre, meta }}
  kpis={[k1, k2, k3]}             // strictement 3
  charts={[chart1, chart2]}       // strictement 2
  highlights={[h1, h2, h3, h4, h5]} // 3-5 obligatoire
  footer={{ sources, confidence, updatedAt }}
/>
```

Validation runtime stricte (cf. doctrine §12.6) avec source-guard CI.

### Priorité 3 — Refonte cockpit/jour Phase 3.4 (~1-2 j-h)

Remplacer `<DecisionEvidenceCard>` agrégée par `<HubPage>` avec 5 `<HubHighlight>` cross-pillar. Nécessite backend diversifié (priorité 1).

### Priorité 4 — Application doctrinale L11 sur 4 hubs restants (~3-4 j-h × 4 = 12-16 j-h)

`/energie` (créer si absent), `/conformite` (refondre Hub Page), `/factures` (refondre Hub Page), `/achat` (créer si absent), `/patrimoine` (créer si absent).

### Priorité 5 — Source-guards CI L11 (~30 min)

`scripts/source_guards_grammar.sh` ajouter :
- **Guard E** `hub-page-uses-canonical-grammar`
- **Guard F** `promeos-marque-correcte` (anti « Promeus », « Proméos », « ProMeos »)

### Priorité 6 — Tests Playwright L11.x cardinaux (~1 j-h)

Visual-grammar suite : tests automatiques L11.1 (3 KPIs), L11.2 (2 charts), L11.3 (verbe invitation), L11.4 (no big table) sur 5 hubs.

## Effort total Phase 3.4

**~17-22 j-h** pour livrer le pattern HubPage canonique sur **5 vues piliers** + tests + source-guards.

ROI attendu : **score sprint 9,2+/10 sur 5 vues cardinales** (vs 8,5+/10 sur 2 vues actuellement).

## Frictions résiduelles à fixer dans Phase 3.4

1. **L4 acronymes bruts** — wrapper « BACS » / « ARENH » / « EMS » / « post-ARENH » via `<Term>` (auto via SolNarrativeText déjà câblé Phase 20.A, mais à garantir sur les rows HubHighlight)
2. **CTA arbitrage global** — ajouter « Lancer la démarche complète CODIR → » sur le hero pour Sophie VC pitch
3. **Score dev 9,2/10** — retirer le bandeau dev-only en mode démo client
4. **Identité PROMEOS** — vérifier orthographe sur sidebar (audit légende sidebar capture : « Proméos » détecté en small-caps Fraunces, conforme tolérance §12.8 mais ambigu — clarifier dans le composant logo)

## Refs

- Capture Proposition A (référence canonique L11)
- `sol_v1_1_addendum_hub_page.md` (source ingéré)
- `docs/vision/promeos_sol_doctrine.md` v1.1 §12 (L11 ingéré ce commit)
- `docs/audits/grammar_v1/BILAN_SPRINT_GRAMMAIRE_V1.md` (bilan global Sprint v1.0 → v1.1)
- Sprint chain : 14 commits Phase 1-3.3.fix livrés · Phase 3.4 candidate documentée
