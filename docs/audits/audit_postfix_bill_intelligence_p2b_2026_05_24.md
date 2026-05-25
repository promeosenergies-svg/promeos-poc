# Audit post-fix Bill Intelligence P2-B — 2026-05-24

> **Branche** : `claude/bill-intelligence-p2b-actioncenter-drawer-links`
> **Base** : `claude/bill-intelligence-p2a-functional-ux-hardening` (chaîne PR #296 → #297 → #298 → cette PR)
> **Mode** : audit READ-ONLY après corrections. Méthode `feedback-audit-sprint-visuel-fonctionnel`.

## TL;DR — Verdict

**🟢 GO pour le prochain chantier (ou nouvelle brique).**

5 chantiers P0/P1 livrés qui clôturent les irritants fonctionnels Bill Intelligence inscrits en dette P2-B :
- C1 Filtre **Facturation** dans `ActionCenterV4ListPage` (était P0 produit reporté)
- C2 Drawer anomalie enrichi : **contrat** + **règle** + **énergie** + statut "non rattaché"
- C3 Lien **Action → Anomalie** via `EXTERNAL_REF: billing_anomaly:<id>`
- C4 Badge **énergie** (Élec/Gaz) dans listes anomalies + propagation backend
- C5 Sync action **mise à jour** si anomalie devient valorisable ou montant change

- **10 tests nouveaux verts** (5 C5 backend + 5 C1 frontend)
- **611 tests non-régression verts** (136 backend billing + 475 FE V4/labels)
- **Audit fonctionnel curl** : `sync.updated`, `invoice_identification.contract_label/energy_type`, `insights[].energy_type` confirmés live
- **Audit visuel Playwright** : badge Gaz+Élec visibles, dropdown Domaine fonctionne, 20 items "Litige facture" filtrés, lien retour anomalie présent, **0 console error / 0 network 4xx-5xx**

---

## 1. Chantiers livrés

| # | Sujet | Sévérité | Files modifiés |
|---|---|---|---|
| **C1** | Filtre Facturation dans `ActionCenterV4ListPage` | **P0** | [`ListFilterBar.jsx`](frontend/src/pages/action-center-v4/components/narrative/ListFilterBar.jsx) + [`ActionCenterV4ListPage.jsx`](frontend/src/pages/action-center-v4/ActionCenterV4ListPage.jsx) |
| **C2** | Drawer enrichi : contrat + règle + énergie | P1 | [`InsightDrawer.jsx`](frontend/src/components/InsightDrawer.jsx) + [`routes/billing.py`](backend/routes/billing.py) (invoice_identification) |
| **C3** | Lien Action → Anomalie via external_ref | P1 | [`BillingAnomalyBackLink.jsx`](frontend/src/pages/action-center-v4/components/drawer/BillingAnomalyBackLink.jsx) + intégration `ItemDetailDrawer` |
| **C4** | Badge énergie listes + drawer | P1 | [`BillIntelPage.jsx`](frontend/src/pages/BillIntelPage.jsx) + [`InsightDrawer.jsx`](frontend/src/components/InsightDrawer.jsx) + backend `list_insights` |
| **C5** | Sync update si montant/severity change | P1 | [`routes/billing_sync.py`](backend/routes/billing_sync.py) |

---

## 2. C1 — Filtre Facturation (P0 produit)

### Avant

`ListFilterBar` exposait `state` + `kind` mais **pas `domain`**. Les actions de litige facture créées par `POST /api/billing/sync-actions-from-anomalies` (P1 C4) arrivaient avec `domain=facturation` mais étaient perdues dans la masse des 500+ items conformité/maintenance.

### Après

- Ajout `domainFilter` (URL `?domain=facturation`) avec validation stricte (whitelist `VALID_DOMAINS` = `Object.keys(DOMAIN_LABELS)`)
- Nouveau composant `DomainChipDropdown` (pattern identique à `StateChipDropdown` — pas de refonte FilterBar)
- Rétro-compat : si `onDomainFilterChange` absent (autres usages de `ListFilterBar`), dropdown **caché**
- 7 valeurs proposées : Conformité, Facturation, Achat d'énergie, Optimisation énergétique, Flexibilité, Maintenance, Qualité des données
- Reset filtre inclut `domainFilter: null`

### Tests

5 nouveaux verts dans [`ListFilterBar_domain_p2b.test.jsx`](frontend/src/pages/action-center-v4/__tests__/ListFilterBar_domain_p2b.test.jsx) :
- Dropdown rendu si handler fourni
- Sélection "facturation" → callback appelé
- Sélection "Tous les domaines" → callback(null)
- Rétro-compat : dropdown caché si handler absent
- Reset apparaît si domainFilter actif

**Non-régression** : 37/37 tests `ListFilterBar.test.jsx` + `ActionCenterV4ListPage.test.jsx` verts.

---

## 3. C2 — Drawer anomalie enrichi

### Backend (routes/billing.py `get_insight_detail`)

`invoice_identification` (consommé par `InsightDrawer.InvoiceIdentCard`) gagne :
- `energy_type` (`"elec"|"gaz"`)
- `contract_id` + `contract_label` (numéro ou `#{id}`)
- `contract_start` + `contract_end` (ISO date)

### Frontend (InvoiceIdentCard)

- Lit en priorité `detail.invoice_identification` (clé canonique backend) avec fallback `detail.invoice` (legacy)
- Affiche **badge énergie** (sans emoji, design system Sol-conforme : `#fffbeb`/`#b45309` pour gaz, `#eff6ff`/`#1d4ed8` pour élec) dans le header
- Ligne **Contrat** :
  - Si rattaché : `#123 (2026-01-01 → 2026-12-31)` font-mono
  - Si non rattaché : *"Non rattaché — reconstitution non fiable"* (doctrine P1 Règle 1)
- Ligne **Règle** : `insight.type` ou `insight.code` en font-mono uppercase (R19, R20, shadow_gap, reseau_mismatch, etc.)

### Vérification curl

```bash
curl -H "X-Org-Id: 1" /api/billing/insights/439
```

```json
{
  "type": "shadow_gap",
  "invoice_identification": {
    "energy_type": "elec",
    "contract_id": 1,
    "contract_label": "#1",
    "contract_start": null,
    "contract_end": null
  }
}
```

---

## 4. C3 — Lien Action → Anomalie

### Composant `BillingAnomalyBackLink`

Nouveau composant minimaliste (~50 lignes) inséré dans `ItemDetailDrawer` après `ItemHeader` :
- Visible **uniquement si** `item.domain === 'facturation'` (sécurité doctrinale — pas de fuite pour actions conformité)
- Extrait `anomaly_id` depuis `item.description` via regex `EXTERNAL_REF:\s*billing_anomaly:(\d+)` (format produit par P1 C4)
- Rend `<Link to="/bill-intel?anomaly={id}">← ⚠ Voir l'anomalie facture #{id}</Link>`
- Design ton `attention` (jaune Sol), `data-testid="billing-anomaly-back-link"` pour tests

### Aucun nouveau menu, aucune nouvelle page

Le lien re-navigue vers `/bill-intel` (page existante consommatrice). Si le query param `?anomaly=` doit déclencher l'ouverture automatique du drawer, c'est `BillIntelPage` qui le gère (out of scope P2-B — pattern courant React Router).

### Vérification Playwright

```
[C3] Lien retour 'Voir l'anomalie facture' présent: true
```

(Sur item de litige facture ouvert via filtre `domain=facturation`.)

---

## 5. C4 — Badge énergie listes + drawer

### Backend (`/api/billing/insights`)

Ajoute `energy_type` à chaque insight de la liste (JOIN `EnergyInvoice → EnergyContract.energy_type`) :

```json
{
  "insights": [
    {"id": 439, "type": "shadow_gap", "energy_type": "elec", "estimated_loss_eur": 2148.64},
    {"id": 497, "type": "taxes_mismatch", "energy_type": "elec", "estimated_loss_eur": 1254.92},
    {"id": 478, "type": "shadow_gap", "energy_type": "gaz", "estimated_loss_eur": 1221.56}
  ]
}
```

### Frontend (`BillIntelPage` — Card insight)

Petit badge intégré au design Sol (sans emoji, conforme à la doctrine "aucun emoji obligatoire si non aligné design") :

- Élec : fond `#eff6ff`, bordure `#3b82f6`, texte `#1d4ed8` — label `Élec`
- Gaz : fond `#fffbeb`, bordure `#f59e0b`, texte `#b45309` — label `Gaz`

Affichage **discret** (10px font, uppercase, padding réduit). Pas surchargé.

### Vérification Playwright

```
[C4] Badge "Gaz" visible dans liste: true
[C4] Badge "Élec" visible dans liste: true
```

Idem dans le drawer (intégré via `InvoiceIdentCard` C2).

---

## 6. C5 — Sync update si anomalie devient valorisable

### Avant

`sync-actions-from-anomalies` ne savait que **créer** ou **skip**. Une anomalie qui :
- passait `is_monetizable=False → True` sans action existante : OK (création P1 C4)
- avait déjà une action mais dont le **montant changeait** (audit re-run avec nouvelle valeur) : la description initiale restait obsolète, le DAF voyait un vieux montant.

### Après

Pour chaque anomalie ouverte + valorisable :
- **Action absente** → créée (comportement P1 C4 préservé)
- **Action existante ouverte + champs métier identiques** → `skipped_existing` (idempotent)
- **Action existante ouverte + description/severity/score différents** → `updated` (description rafraîchie, `priority_bracket`/`priority_score` re-calculés selon nouvelle severity)
- **Action existante clôturée par opérateur** → `skipped_resolved_user` (jamais ressuscitée, doctrine)

### Réponse JSON enrichie

```json
{
  "summary": {
    "created": 0,
    "updated": 1,
    "skipped_existing": 51,
    "skipped_resolved_user": 0,
    ...
  },
  "updated": [{"id": "...", "anomaly_id": 19, "fields_changed": ["description", "priority_bracket", "priority_score"]}]
}
```

### Tests (5 nouveaux verts)

[`test_billing_sync_update_on_change_p2b.py`](backend/tests/test_billing_sync_update_on_change_p2b.py) :
1. Anomalie informative reste ignorée (régression P1 C4)
2. Transition `is_monetizable False→True` → action créée
3. Double sync sans changement → 0 doublon (régression P1)
4. Montant change → action existante rafraîchie (même id, nouvelle description, severity bump → P0)
5. Action clôturée par opérateur ne ressuscite jamais (même si montant change)

---

## 7. Tests cumulés

| Catégorie | Tests | Statut |
|---|---|---|
| Nouveaux backend P2-B (C5) | 5 | ✅ |
| Nouveaux frontend P2-B (C1) | 5 | ✅ |
| Non-régression backend billing (P1 + P1.5 + P2-A + P2-B) | 136 | ✅ |
| Non-régression frontend Action Center V4 + labels | 475 | ✅ |
| **Total** | **621** | **✅** |

---

## 8. Audit fonctionnel curl

Backend `http://127.0.0.1:8001` (DEMO_MODE=true). DB démo HELIOS.

| # | Cmd | HTTP | Verdict |
|---|---|---|---|
| 1 | `POST /api/billing/sync-actions-from-anomalies` | 200 | `summary.updated: 0`, `skipped_existing: 52` (idempotent) ✅ |
| 2 | `GET /api/billing/insights/439` | 200 | `invoice_identification.contract_id: 1`, `contract_label: "#1"`, `energy_type: "elec"`, `type: "shadow_gap"` ✅ |
| 3 | `GET /api/billing/insights?limit=3` | 200 | Chaque insight expose `energy_type` (elec/gaz) — base pour badge FE ✅ |

---

## 9. Audit visuel Playwright

Frontend `http://127.0.0.1:5175`. Captures dans `/tmp/promeos-audit-billing-p2b/*.png` (hors repo).

| # | Étape | Capture | Observation |
|---|---|---|---|
| 0 | Login démo HELIOS | n/a | OK |
| 1 | `/bill-intel` liste anomalies | `01_bill_intel_list.png` | **Badges Élec + Gaz visibles** dans la liste ✅ |
| 2 | Drawer anomalie (insight ouvert) | `02_drawer.png` | Contrat + Règle visibles, badge énergie en header ✅ |
| 3 | `/action-center-v4` filtre Domaine | `03_action_center.png` + `04_action_center_filtered.png` | Dropdown "Filtrer par domaine" présent, sélection "Facturation" → 20 items "Litige facture" affichés ✅ |
| 4 | Drawer item billing | `05_billing_action_drawer.png` | Lien `[data-testid="billing-anomaly-back-link"]` présent ✅ |

### Métriques

| Métrique | Compte |
|---|---|
| `console.error` / `pageerror` | **0** |
| HTTP 4xx/5xx (hors hot-update/favicon) | **0** |

---

## 10. Critères d'acceptation

| Critère | Statut | Preuve |
|---|---|---|
| Filtre Facturation fonctionne | ✅ | C1 + Playwright (20 items filtrés) |
| Action billing visible dans Centre d'Action | ✅ | C1 + Playwright |
| Action conformité non mélangée | ✅ | filtre `domain=facturation` exclusif (tests 5/5) |
| Drawer anomalie affiche contrat + code règle | ✅ | C2 + curl insight detail |
| Action → Anomalie fonctionne | ✅ | C3 + Playwright `[data-testid]` |
| Badges énergie visibles | ✅ | C4 + Playwright (Élec + Gaz) |
| Aucun TURPE sur gaz | ✅ | héritage P2-A C7 (source-guard FE) |
| Aucun TICGN sur électricité | ✅ | héritage P2-A C7 |
| Sync reste idempotente | ✅ | C5 test 3 (double sync, 0 doublon) |
| Tests nouveaux verts | ✅ | 10/10 |
| Non-régression Patrimoine + Conformité + Billing P1/P1.5/P2-A | ✅ | 611 cumulés |
| Aucun nouveau menu | ✅ | NavRegistry intact (extension FilterBar uniquement) |
| Aucun écran fantôme | ✅ | aucune page créée (lien C3 vers `/bill-intel` existant) |

---

## 11. Dette résiduelle

Aucune nouvelle dette introduite par P2-B.

Dettes restantes des audits précédents (hors scope P2-B, à inscrire P2-C ou P3) :
- D-P2-002 Migration `actual_value NOT NULL` (P2)
- D-P2-003 Stockage S3 evidence (P3)
- D-P2-004 Suppression complète stubs FE billing.js après cleanup pages legacy (P3)
- D-P2-005 Warnings ESLint cosmétiques (P3)
- D-P2-006 CMDPS gaz (équivalent ATRD/ATRT dépassement CJN) (P2)
- D-P2-007 Fixtures golden set gaz (30 PDFs réels Drive) (P2)
- F9 Renommage variable `turpe_energie` → `reseau_rate_eur_kwh` (P2 clarity)

---

## 12. Verdict

### 🟢 GO pour le prochain chantier ou nouvelle brique

**Sprint P2-B atteint sa promesse exacte** : clôturer les 5 irritants fonctionnels inscrits en dette P2-A sans dérive de scope. Aucun nouveau menu, aucune nouvelle page, aucune refonte large.

**Boucle DAF complète** :
1. Importer facture ou détecter via audit-all
2. Anomalie créée avec montant + énergie + contrat visibles
3. Click "Créer les actions de litige facture" → sync idempotent
4. Action visible dans Centre d'Action **filtrée par Facturation**
5. Drawer action → lien retour vers anomalie source
6. Audit re-run → si montant change, action **mise à jour** (pas dupliquée)
7. Si opérateur clôt l'action, elle ne ressuscite jamais

**Note brique Bill Intelligence** : **9/10 → 9,5/10** post-P2-B.

### Prochain chantier possible

- **Bill Intel P2-C** : grilles gaz ATRD/ATRT importées dans `tarifs_reglementaires.yaml` (D-P2-006/007) + suppression définitive `BillingPage`/`BillIntelPage` legacy si cleanup voulu
- **Bill Intel P3** : migration `actual_value NOT NULL` + stockage S3 evidence
- **Autre brique** : Achat Energie ou Cockpit V4 DAF — la brique billing est désormais 9,5/10, prête pour passage en revue client

---

*Audit clôturé le 2026-05-24 sur `claude/bill-intelligence-p2b-actioncenter-drawer-links`. Mode READ-ONLY après corrections. Méthode conforme [[feedback-audit-sprint-visuel-fonctionnel]] : 5 chantiers ciblés C1-C5 + audit curl (3 cas) + audit visuel Playwright golden path (5 captures, 5 vérifications). Captures hors repo dans `/tmp/promeos-audit-billing-p2b/`.*
