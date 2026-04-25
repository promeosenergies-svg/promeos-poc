# Audit API /compliance/pipeline — Lot 6 Phase 5 pré-flight

> **Date** : 2026-04-19
> **Contexte** : dernière cible Lot 6 (4/4). Page `/compliance/pipeline` = pipeline temps réel portfolio DT × BACS × APER. Éviter 8ᵉ remap + scope creep final.

## 1. Git ahead clarification

```
51 commits ahead · 0 behind origin/main
  - 50 applicatifs
  - 1 merge commit (01e30023 · merge origin/main Yannick VNU)
```

Estimation DoD Phase 4 "ahead 54" était optimiste. Le nombre réel est 51, **non-bloquant** car `behind 0` = branche refonte contient intégralement l'état `main`.

## 2. Page legacy identifiée

| Champ | Valeur |
|---|---|
| Route | `/compliance/pipeline` (App.jsx:429) |
| Composant | `frontend/src/pages/CompliancePipelinePage.jsx` |
| LOC | **369 lignes** |
| Lazy-loaded | ✅ (App.jsx:95) |
| Hooks | `useScope`, `useActionDrawer`, `useToast` |
| API | `getPortfolioComplianceSummary({site_id?})` |
| Drawer legacy | ActionDrawer via `useActionDrawer()` (context global — préservable via reuse, pas d'inline à extraire) |
| Modals | aucun modal spécifique (contrairement à EfaSol ExportOperatModal) |

## 3. Endpoint API confirmé

**URL réelle** : `GET /api/compliance/portfolio/summary`

(NB : la spec prompt mentionnait `/api/v1/regops/compliance-portfolio?org_id=1` qui N'EXISTE PAS — même piège qu'en Phase 4 avec les endpoints v1. Le vrai endpoint est `/api/compliance/portfolio/summary` sans préfixe v1.)

### Shape complète observée (HELIOS, org_id=1, 5 sites)

```json
{
  "org_id": 1,
  "total_sites": 5,
  "kpis": {
    "data_blocked": 0,
    "data_warning": 0,
    "data_ready": 5
  },
  "top_blockers": [],
  "deadlines": {
    "d30": [
      {
        "type": "finding",
        "regulation": "bacs",
        "description": "CVC > 290 kW, échéance 01/01/2025 — attestation BACS manquante",
        "deadline": "2025-01-01",
        "statut": "NOK",
        "days_remaining": -473,
        "site_id": 1,
        "site_nom": "Siège HELIOS Paris"
      }
    ],
    "d90": [ { /* 1 APER ombrière PV 2026-07-01 · days_remaining 73 */ } ],
    "d180": [ { /* 1 DT trajectoire -40% 2026-09-30 · days_remaining 164 */ } ],
    "beyond": [
      /* 7 échéances > 180 j : BACS 2030 (×2), DT 2030 OPERAT (×5) */
    ]
  },
  "untrusted_sites": [
    {
      "site_id": 1,
      "site_nom": "Siège HELIOS Paris",
      "trust_score": 0,
      "anomaly_count": 16,
      "reasons": ["10 anomalie(s) élevée(s)"]
    }
    /* 3 autres sites avec trust_score 0-32 */
  ],
  "sites": [
    {
      "site_id": 1,
      "site_nom": "Siège HELIOS Paris",
      "gate_status": "OK",
      "completeness_pct": 100.0,
      "reg_risk": 10,
      "compliance_risk_score": 10,
      "compliance_score": 90,
      "financial_opportunity_eur": 0.0,
      "applicability": {
        "tertiaire_operat": true,
        "bacs": true,
        "aper": true
      }
    }
    /* 4 autres sites : Bureau Lyon 85 · Entrepôt Toulouse 45 · Hôtel Nice 100 · École Marseille 55 */
  ]
}
```

### Champs disponibles (riche — contrairement à Phase 4)

- ✅ `total_sites` : compteur agrégat
- ✅ `kpis.data_blocked / data_warning / data_ready` : gate-status agrégat ORG
- ✅ `deadlines.d30 / d90 / d180 / beyond` : 4 buckets timeline avec countdown
- ✅ `untrusted_sites[]` : liste avec trust_score + anomaly_count + reasons
- ✅ `sites[]` : liste complète avec compliance_score par site + completeness + reg_risk + financial_opportunity + applicability DT/BACS/APER
- ✅ `top_blockers[]` : array (vide dans HELIOS mais shape prête)

**Pas de 8ᵉ remap nécessaire**. Shape expose directement tout ce dont le hero a besoin. Discipline honnêteté Lot 6 = 7/7 remaps stable.

## 4. Hypothèse cadre Pattern retenue

### H1 — Pattern B + SolKpiRow agrégats (recommandé, scope aligné)

- SolListPage wrapper
- **3 KPIs Sol** lus directement depuis `kpis` + `deadlines` + `untrusted_sites.length` :
  - KPI 1 « Sites prêts » : `kpis.data_ready / total_sites` · tone succes si 100 %
  - KPI 2 « Échéances < 30 j » : `deadlines.d30.length` · tone refuse si > 0, attention si d90 > 0, calme sinon
  - KPI 3 « Sites non fiables » : `untrusted_sites.length / total_sites` · tone refuse si > 50 %, attention si > 0, succes si 0
- SolExpertToolbar : search + filtres (gate_status · applicability framework · trust) + activeFilterCount
- SolExpertGridFull 8 cols : Site · Gate · Complétude % · Score conformité · Risque · Opportunité € · Tertiaire ✓/✗ · BACS ✓/✗ · APER ✓/✗
- Default sort : `compliance_score` ASC (les moins conformes en haut = signal DAF)
- onRowClick → navigate `/sites/:id?tab=compliance` (site360 detail)
- SolPagination (mais 5 sites HELIOS → pas pertinente, rendue null par composant)

### H2 — Pattern B + preludeSlot Timeline deadlines (option enrichie)

Ajoute un preludeSlot au-dessus de la toolbar qui affiche SolTimeline (reuse Lot 3 P4) avec 4 buckets d30/d90/d180/beyond en jalons verticaux. Donne une vue temporelle avant la table.

### Recommandation

**H1 pour v2.4 (dernière cible Lot 6)** · H2 option Phase 6+ si signal pilote (preludeSlot Timeline ajoute ~50 lignes + 30 min de calibration jalons, pas critique pour démo).

Choix H1 aligne sur :
- Scope Phase 5 = 1 commit atomique comme Phases 2/3 (KB + Segmentation)
- Discipline « même niveau d'exigence que 1/4 » — pas de scope creep final
- Reuse total Pattern B Lot 2 (SolListPage + Toolbar + GridFull + KpiRow + Pagination)

## 5. Patterns interdits (source-guards TDD Phase 5.0)

À interdire côté front (tous absents par nature car backend-sourced) :

| Pattern | Raison |
|---|---|
| `reg_risk\s*[+*]\s*0\.[0-9]` | Pas de pondération client-side de reg_risk |
| `compliance_score\s*=\s*[0-9]{2}` | Pas d'assignation littérale score |
| `completeness_pct\s*[><]=?\s*(50|75|90|100)` | Seuils completeness viennent du backend gate_status |
| `trust_score\s*[<>]\s*[0-9]+` | Filtre trust = via applicability `untrusted_sites` array (pas seuil formule) |
| `financial_opportunity_eur\s*\*` | Pas d'agrégat multiplicatif fantôme |
| hardcoded dates DT/BACS/APER (2025/2026/2028/2030) dans formules | Dates issues de deadlines[].deadline backend |

Whitelist findings.ops identique Phase 4 : enums `regulation/statut/gate_status/site_nom` autorisés en display.

## 6. Glossary + business_errors à créer (≈5 + 3)

Glossary candidats Phase 5 :
- `pipeline_sites_ready` (sites data-gate OK / total)
- `pipeline_deadlines_d30` (échéances imminentes < 30 j)
- `pipeline_untrusted_sites` (sites avec trust_score < 50)
- `pipeline_gate_status` (OK / WARNING / BLOCKED enum)
- `pipeline_applicability_frameworks` (DT/BACS/APER par site)

business_errors candidats :
- `pipeline.no_sites` (portfolio vide)
- `pipeline.filter_no_results` (filtres actifs sans résultat)
- `pipeline.all_ready` (succes · aucune action urgente)

## 7. Ordre exécution Phase 5 proposé (1 commit atomique par sous-phase)

| # | Livrable | Estimation | Gate |
|---|---|---|---|
| P5.0 | Source-guards TDD (pytest + vitest scope) | 15 min | 6+ patterns + 1 scope guard verts |
| P5.1 | `pipeline/sol_presenters.js` (~150 L, 9+ helpers) + unit tests | 30 min | ≥ 15 cases vitest |
| P5.2 | `CompliancePipelineSol.jsx` (~180 L) | 30 min | Pattern B complet · 4 états |
| P5.3 | Intégration CompliancePipelinePage legacy · hideHeader · legacy body wrapped `{false && (…)}` | 15 min | Diff +X/-0 sur fonctionnel legacy |
| P5.4 | Glossary +5 · business_errors +3 · A/B capture · commit final | 15 min | DoD complet |

**Total estimé : ~1 h 45 min**. Aligné budget Phase 5 (sous-2 h · dernière cible).

## 8. Discipline surveillance user (rappel Lot 6)

- R1 build heap : circular toujours infirmé · workaround `NODE_OPTIONS=6144` stable
- R2 remap : shape API expose tout · **aucun 8ᵉ remap attendu** · STOP GATE SI émergence pendant P5.1
- R3 code-review + simplify : à invoquer à chaque STOP gate P5.0 → P5.4

## 9. Écart main post-Phase 5

Prévision : `ahead ≥ 56, behind 0` après 5 commits Phase 5 (pré-flight + P5.0-5.4 fusionnés possibles).
