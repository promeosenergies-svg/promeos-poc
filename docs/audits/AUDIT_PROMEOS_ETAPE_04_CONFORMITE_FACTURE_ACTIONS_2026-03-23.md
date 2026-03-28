# AUDIT PROMEOS — ÉTAPE 4 : CONFORMITÉ → FACTURE → ACTIONS

> **Date** : 2026-03-23
> **Baseline** : Étapes 0-3 + FIX 3 + FIX 3B
> **Méthode** : Grep exhaustif bilatéral (conformité↔billing, 3 agents parallèles), trace modèle de données, cartographie CTA
> **Statut** : AUDIT UNIQUEMENT — aucune modification du repo

---

## 1. Résumé exécutif

Le maillon **Conformité → Facture** reste la **rupture la plus grave** du fil conducteur PROMEOS. C'est un **trou architectural**, pas un bug. Les deux domaines sont des **silos indépendants** qui partagent uniquement un ancrage `Site` et un point de convergence au niveau de l'Action Hub.

**Le paradoxe** : PROMEOS dispose d'un Action Hub sophistiqué (4 builders, dedup SHA-256, deep-linking, workflow OPEN→IN_PROGRESS→DONE, evidence gate, audit trail) mais les **deux briques qu'il fédère ne se parlent pas directement**. L'intégration est réelle au niveau des actions, mais inexistante au niveau métier.

| Lien | Statut | Preuve |
| --- | --- | --- |
| Conformité → Facture (backend) | **ABSENT** | 0 import croisé (grep exhaustif) |
| Conformité → Facture (frontend) | **ABSENT** | 0 référence (grep exhaustif) |
| Conformité → Actions | **IMPLÉMENTÉ** | `build_actions_from_compliance()` + bouton "Créer action" + deep-link retour |
| Facture → Actions | **IMPLÉMENTÉ** | `build_actions_from_billing()` + bouton "Créer action" (avec prefill) + deep-link retour |
| Actions → Source (reverse) | **IMPLÉMENTÉ** | `buildSourceDeepLink()` → `/conformite` ou `/bill-intel` |
| Cockpit risque billing | **PLACEHOLDER** | `billing_anomalies_eur: 0` hardcodé dans `cockpit.py:185` |

---

## 2. Cartographie réelle des liens

```text
                    CONFORMITÉ              FACTURE
                    ══════════              ═══════

          ComplianceFinding            BillingInsight
          (site_id, status,            (site_id, type,
           severity, rule_id,           severity, estimated_loss_eur,
           estimated_penalty_eur)       recommended_actions_json)
                    │                          │
                    │ build_actions_            │ build_actions_
                    │ from_compliance()         │ from_billing()
                    │                          │
                    ▼                          ▼
              ┌──────────────────────────────────────┐
              │           ACTION HUB                  │
              │  action_hub_service.py:258-388         │
              │  sync_actions() → dedup → persist     │
              │                                        │
              │  ActionItem (source_type, source_id,   │
              │   source_key, title, severity,         │
              │   estimated_gain_eur, priority)         │
              │                                        │
              │  Dedup: (org_id, source_type,          │
              │          source_id, source_key)         │
              └──────────────────────────────────────┘
                    │                          │
                    ▼                          ▼
              source_deeplink            source_deeplink
              → /conformite              → /bill-intel
              ?tab=obligations

                    ╳ AUCUN LIEN DIRECT ╳

    ConformitePage ────────╳──────── BillIntelPage
    0 ref billing                    0 ref compliance
    0 import billing                 0 import compliance
    0 CTA vers facture               0 CTA vers conformité
```

---

## 3. Liens réellement implémentés

### 3.1 Conformité → Actions — IMPLÉMENTÉ

**Backend** : `action_hub_service.py:79-122`

```python
# build_actions_from_compliance()
findings = db.query(ComplianceFinding).filter(
    ComplianceFinding.site_id.in_(site_ids),
    ComplianceFinding.status == "NOK",
    ComplianceFinding.insight_status != InsightStatus.FALSE_POSITIVE,
)
# Pour chaque finding NOK : parse recommended_actions_json
# source_type = ActionSourceType.COMPLIANCE
# source_id = str(finding.id)
# source_key = f"{finding.rule_id}:{idx}"
# severity = finding.severity
# due_date = finding.deadline
```

**Frontend** : ConformitePage.jsx
- Bouton "Créer une action" (`openActionDrawer`) — ligne 554
- ConformiteSummaryBanner : CTA "Voir le plan d'action" → `/actions` — ligne 125
- ExecutionTab : CTA plan d'actions → `/anomalies?tab=actions` — ligne 173
- ObligationsTab : "Créer action" depuis obligation — ligne 700+

**Deep-link retour** : `buildSourceDeepLink('compliance', sourceId)` → `/conformite?tab=obligations`

**Tag** : IMPLÉMENTÉ — Chaîne complète (finding NOK → action persistée → deep-link retour)

### 3.2 Facture → Actions — IMPLÉMENTÉ

**Backend** : `action_hub_service.py:173-217`

```python
# build_actions_from_billing()
insights = db.query(BillingInsight).filter(
    BillingInsight.site_id.in_(site_ids),
    BillingInsight.insight_status != InsightStatus.FALSE_POSITIVE,
    BillingInsight.recommended_actions_json.isnot(None),
)
# source_type = ActionSourceType.BILLING
# source_id = str(insight.id)
# source_key = f"{insight.type}:{idx}"
# estimated_gain_eur = insight.estimated_loss_eur  ← PROPAGÉ
```

**Frontend** : BillIntelPage.jsx:392-418

```javascript
openActionDrawer({
  prefill: {
    titre: insight?.message,
    type: 'facture',
    impact_eur: insight?.estimated_loss_eur,
  },
  sourceType: 'billing',
  sourceId: String(insight.id),
  idempotencyKey: `billing-insight:${insight.id}`,  // ← IDEMPOTENT
})
```

**Deep-link retour** : `buildSourceDeepLink('billing', sourceId)` → `/bill-intel`

**Tag** : IMPLÉMENTÉ — Chaîne complète (insight → action + prefill + idempotency + deep-link)

### 3.3 Actions → Source (reverse navigation) — IMPLÉMENTÉ

**Backend** : `routes/actions.py:121-143`

```python
def _source_deeplink(source_type, source_id):
    if val == "compliance": return "/conformite?tab=obligations"
    if val == "billing":    return "/bill-intel"
    if val == "consumption": return "/consommations/explorer"
    if val == "purchase":   return "/achats"
```

**Frontend** : `ActionDetailDrawer.jsx` affiche `source_label` + `source_deeplink` dans chaque action.

**Tag** : IMPLÉMENTÉ

---

## 4. Liens partiels

### 4.1 Site360 : tabs côte à côte sans cross-référence — PARTIEL

Site360 a 6 tabs : Resume, Conso, Factures, Reconciliation, Conformité, Actions.

- Le tab Resume affiche `risque_financier_euro` (compliance-driven) ET des liens vers billing et conformité
- Les tabs Factures et Conformité sont **séparés sans partage de données**
- Le tab Actions regroupe toutes les actions du site (compliance + billing + purchase)

**Tag** : PARTIEL — Juxtaposé, pas intégré. L'utilisateur voit les deux mondes mais ne comprend pas le lien.

### 4.2 Cockpit : KPIs compliance + billing juxtaposés — PARTIEL

`cockpit.py:174-188` retourne :
```python
"risque_breakdown": {
    "reglementaire_eur": round(risque_total, 2),      # ← CALCULÉ (compliance)
    "billing_anomalies_eur": 0,                         # ← HARDCODÉ À 0
    "contract_risk_eur": 0,                             # ← HARDCODÉ À 0
    "total_eur": round(risque_total, 2),
}
```

Le cockpit *prétend* décomposer le risque (réglementaire + billing + contrat) mais `billing_anomalies_eur` et `contract_risk_eur` sont **toujours à 0**.

**Tag** : COSMÉTIQUE SEULEMENT — Structure de données prometteuse mais non câblée

---

## 5. Liens absents

### 5.1 Conformité → Facture (backend) — ABSENT

| Recherche | Résultat | Fichier |
| --- | --- | --- |
| "billing" dans compliance_engine.py | 0 | compliance_engine.py |
| "billing" dans compliance_score_service.py | 0 | compliance_score_service.py |
| "billing" dans compliance_coordinator.py | 0 | compliance_coordinator.py |
| "billing" dans regops/engine.py | 0 | regops/engine.py |
| "compliance" dans billing_service.py | 0 | billing_service.py |
| "compliance" dans billing_shadow_v2.py | 0 | billing_shadow_v2.py |
| "compliance" dans billing_engine/engine.py | 0 | billing_engine/engine.py |
| FK ComplianceFinding → BillingInsight | 0 | models/ |
| FK BillingInsight → ComplianceFinding | 0 | models/ |

**Tag** : ABSENT — Zéro lien backend. Les deux domaines ne s'importent pas, ne se référencent pas, ne partagent aucune FK.

### 5.2 Conformité → Facture (frontend) — ABSENT

| Recherche | Résultat | Fichier |
| --- | --- | --- |
| "billing"/"facture"/"invoice"/"bill-intel" dans ConformitePage.jsx | 0 | ConformitePage.jsx |
| "compliance"/"conformite"/"obligation"/"risque" dans BillIntelPage.jsx | 0 | BillIntelPage.jsx |
| "billing"/"facture" dans conformite-tabs/*.jsx | 0 | ObligationsTab, DonneesTab, ExecutionTab, PreuvesTab |

**Tag** : ABSENT — Zéro lien frontend. Aucun CTA, aucun import, aucune donnée partagée.

### 5.3 Risque financier dans les vues facture — ABSENT

`risque_financier_euro` (calculé par compliance_engine) n'est affiché **nulle part** dans BillIntelPage ou BillingPage. Il apparaît uniquement dans :
- Cockpit (KPI global)
- ConformitePage (badge risque)
- Site360 Resume tab (mini-KPI)

**Tag** : ABSENT — Le risque réglementaire n'est pas contextualisé dans la vue facture

---

## 6. CTA, navigation et UX inter-briques

### Matrice de navigation existante

| Depuis | Vers Conformité | Vers Facture | Vers Actions |
| --- | --- | --- | --- |
| **Cockpit** | ✅ CTA compliance KPI | ✅ CTA billing anomalies | ✅ CTA plan d'action |
| **ConformitePage** | — | ❌ AUCUN | ✅ "Créer action" + CTA plan |
| **BillIntelPage** | ❌ AUCUN | — | ✅ "Créer action" (prefill) |
| **ActionsPage** | ✅ deep-link `/conformite` | ✅ deep-link `/bill-intel` | — |
| **Site360** | ✅ tab Conformité | ✅ tab Factures | ✅ tab Actions |
| **PurchasePage** | ❌ | ✅ "Contrôler facture" | ❌ (éphémère) |

**Lacune critique** : Le "triangle stratégique" Conformité ↔ Facture ↔ Actions n'a que **2 côtés câblés** (Conformité→Actions et Facture→Actions). Le 3e côté (Conformité↔Facture) est **totalement absent**.

### Helpers de navigation

`routes.js` fournit `toBillIntel()`, `toActionsList()`, `toActionNew()`, `toConsoExplorer()`, `toPurchase()` — **mais pas de `toConformite()`** helper. La navigation vers conformité se fait par URL directe (`/conformite`).

**Tag** : PARTIEL — Navigation fonctionnelle via Actions, mais pas de lien direct Conformité↔Facture

---

## 7. Modèle de données et traçabilité

### Architecture des liens

```text
Organisation
    └── Site (id)
          ├── ComplianceFinding (site_id, status, severity, rule_id, deadline)
          │     └── NO FK to billing
          ├── BillingInsight (site_id, type, severity, estimated_loss_eur)
          │     └── NO FK to compliance
          ├── Obligation (site_id, type, statut, avancement_pct)
          │     └── NO FK to billing
          ├── EnergyInvoice (site_id, contract_id, energy_kwh, total_eur)
          │     └── NO FK to compliance
          └── ActionItem (site_id, source_type, source_id, source_key)
                ├── source_type = COMPLIANCE → traces ComplianceFinding
                ├── source_type = BILLING → traces BillingInsight
                ├── source_type = CONSUMPTION → traces ConsumptionInsight
                └── source_type = PURCHASE → traces purchase actions
```

**Le seul lien transverse** = `site_id`. Les deux domaines partagent le même site mais sans aucune jointure métier.

**ActionItem** est le **seul modèle qui fédère** les deux domaines, via `source_type` discriminant. Mais un ActionItem de type COMPLIANCE ne contient aucune référence à un BillingInsight, et vice-versa.

### Sources de vérité

| Donnée | Source unique | Fichier |
| --- | --- | --- |
| Risque financier | `compliance_engine.py:214-216` (7500 × NOK + 3750 × RISK) | compliance_engine.py |
| Score conformité A.2 | `compliance_score_service.py` (DT 45% + BACS 30% + APER 25%) | compliance_score_service.py |
| Anomalies facture | `billing_service.py` (14 règles) | billing_service.py |
| Actions unifiées | `action_hub_service.py` (4 builders + dedup) | action_hub_service.py |

**Tag** : IMPLÉMENTÉ (sources de vérité claires) mais ABSENT (pas de lien croisé entre elles)

---

## 8. KPI / vues / workflows trompeurs

### T1 : Cockpit `risque_breakdown` = placeholder

`cockpit.py:185-186` retourne `billing_anomalies_eur: 0` et `contract_risk_eur: 0` — des champs qui **existent dans la structure mais sont hardcodés à 0**. L'UI pourrait les afficher comme "pas de risque billing" alors qu'en réalité ils ne sont simplement pas calculés.

**Tag** : COSMÉTIQUE SEULEMENT — Structure prometteuse mais non câblée

### T2 : Site360 donne une illusion d'intégration

Site360 affiche 6 tabs (Resume, Conso, Factures, Reconciliation, Conformité, Actions) côte à côte, ce qui donne l'impression que les données sont liées. En réalité, chaque tab charge ses données de façon indépendante, sans partage ni contexte croisé.

**Tag** : À RISQUE UX — L'utilisateur pourrait croire à une vue intégrée alors que c'est une juxtaposition

### T3 : Le récit "risque conformité → impact financier" s'arrête au cockpit

Le cockpit affiche `risque_financier_euro` (compliance-driven). Un utilisateur qui clique pour comprendre ce chiffre atterrit sur ConformitePage — qui ne mentionne aucune facture. L'utilisateur ne peut pas relier le risque à une facture concrète.

**Tag** : À RISQUE CRÉDIBILITÉ — Le récit se casse à la 3e étape

---

## 9. Sources vérifiées

Pas de point réglementaire sensible dans cette étape — l'audit porte sur l'architecture du lien inter-briques, pas sur les taux ou deadlines.

Les sources réglementaires des étapes 2 et 3 restent valides (TICGN versionnée, TURPE 7 CRE n°2025-78, seuils DT/BACS/APER).

---

## 10. Top P0 / P1 / P2

### P0 — Bloquant crédibilité démo

| # | Problème | Impact | Correctif recommandé | Effort |
| --- | --- | --- | --- | --- |
| P0-1 | **Conformité → Facture = 0 lien** | Triangle stratégique cassé. En démo : "et la facture ?" = question sans réponse | Ajouter bandeau risque financier dans BillIntelPage quand site non-conforme + CTA "Voir conformité" | **S** |
| P0-2 | **Facture → Conformité = 0 lien** | Même rupture dans l'autre sens | Ajouter CTA "Voir factures" dans ConformitePage quand des factures existent | **XS** |

### P1 — Crédibilité marché

| # | Problème | Impact | Correctif | Effort |
| --- | --- | --- | --- | --- |
| P1-1 | `billing_anomalies_eur` hardcodé à 0 dans cockpit | Risque billing invisible dans le risque global | Calculer `SUM(BillingInsight.estimated_loss_eur)` scoped | S |
| P1-2 | Site360 tabs Factures et Conformité sans cross-référence | Juxtaposition trompeuse | Mini-KPI conformité dans tab Factures, mini-KPI facture dans tab Conformité | S |
| P1-3 | Pas de helper `toConformite()` dans routes.js | Navigation vers conformité = URL brute | Créer helper avec scope params | XS |

### P2 — Premium

| # | Problème | Impact | Correctif | Effort |
| --- | --- | --- | --- | --- |
| P2-1 | Pas de modèle de liaison métier Finding↔Insight | Impossible de relier une non-conformité DT à une dérive de facture | Créer une vue "Impact financier" croisant obligations + factures par site | L |
| P2-2 | Actions compliance sans estimated_gain_eur | Toutes les actions compliance ont gain=None vs billing actions qui ont estimated_loss | Calculer gain potentiel = pénalité évitée (7500€) si remédié | S |
| P2-3 | Pas de vue "conformité + facture" intégrée | Le récit bout-en-bout nécessite 3 onglets/pages | Dashboard site unifié avec risque total (réglementaire + billing + contrat) | L |

---

## 11. Plan de correction priorisé

### Immédiat (1-2 jours) — XS/S

| # | Action | Fichier | Effort |
| --- | --- | --- | --- |
| 1 | **CTA "Voir conformité" dans BillIntelPage** quand site a statut NON_CONFORME ou A_RISQUE | `BillIntelPage.jsx` | XS |
| 2 | **CTA "Voir factures" dans ConformitePage** | `ConformitePage.jsx` | XS |
| 3 | **Helper `toConformite()`** dans routes.js avec scope params | `routes.js` | XS |
| 4 | **Bandeau risque financier dans BillIntelPage** si `site.risque_financier_euro > 0` | `BillIntelPage.jsx` | S |

### Court terme (1 semaine) — S/M

| # | Action | Fichier | Effort |
| --- | --- | --- | --- |
| 5 | **Calculer `billing_anomalies_eur`** = `SUM(BillingInsight.estimated_loss_eur WHERE insight_status=OPEN)` dans cockpit.py | `cockpit.py:185` | S |
| 6 | **Mini-KPI conformité dans tab Factures de Site360** (score conformité + statut DT/BACS) | `Site360.jsx` | S |
| 7 | **Mini-KPI facture dans tab Conformité de Site360** (nb anomalies + perte estimée) | `Site360.jsx` | S |
| 8 | **Actions compliance avec estimated_gain_eur** = pénalité évitable | `action_hub_service.py:104` | S |

### Moyen terme (2-4 semaines) — L

| # | Action | Fichier | Effort |
| --- | --- | --- | --- |
| 9 | **Vue "Impact financier"** croisant obligations non-conformes + anomalies facture par site | Nouveau composant | L |
| 10 | **Risque total calculé** = réglementaire + billing_anomalies + contract_risk dans cockpit | `cockpit.py`, `kpi_service.py` | M |

---

## 12. Definition of Done

| Critère | Statut |
| --- | --- |
| Lien Conformité→Facture backend audité | FAIT — 0 lien (grep exhaustif confirmé) |
| Lien Conformité→Facture frontend audité | FAIT — 0 lien (grep exhaustif confirmé) |
| Lien Conformité→Actions audité | FAIT — IMPLÉMENTÉ (builder + bouton + deep-link) |
| Lien Facture→Actions audité | FAIT — IMPLÉMENTÉ (builder + prefill + idempotency + deep-link) |
| Actions→Source reverse audité | FAIT — IMPLÉMENTÉ (buildSourceDeepLink) |
| Cockpit risque_breakdown audité | FAIT — COSMÉTIQUE (billing=0 hardcodé) |
| Site360 cross-tabs audité | FAIT — PARTIEL (juxtaposé) |
| Navigation CTA cartographiée | FAIT — Triangle 2/3 câblé |
| Modèle de données tracé | FAIT — Site seul point commun, ActionItem fédérateur |
| P0/P1/P2 priorisés | FAIT — 2 P0, 3 P1, 3 P2 |
| Plan de correction avec fichiers | FAIT — 10 actions, XS à L |

---

*Audit étape 4 réalisé le 2026-03-23. Les 2 P0 (CTA croisés Conformité↔Facture) sont les quick wins à plus fort impact pour le récit démo.*
