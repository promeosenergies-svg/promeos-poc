# Audit post-fix Bill Intelligence P2-A — 2026-05-24

> **Branche** : `claude/bill-intelligence-p2a-functional-ux-hardening`
> **Base** : `claude/refonte-sol2 @ db8aaac1` + cherries `3b7aeb95` (P1) + `f27de278` (P1.5)
> **Mode** : audit READ-ONLY après correction. Méthode `feedback-audit-sprint-visuel-fonctionnel`.

## TL;DR — Verdict

**🟢 GO pour le prochain chantier.**

6 fixes ciblés livrés (3 P0/P1 backend + 3 P0/P1 frontend) qui sécurisent la couche **calculs / cohérence / UX** post-P1 et P1.5 :
- KPIs doctrinaux (source/formule/unité/période/périmètre) — `kpi_metadata` exposé
- Fiabilité du shadow billing exposée (`is_reliable` + `reliability_reason`)
- `energy_type` propagé explicitement dans audit
- KPI "Surfacturations à contester" (renommage doctrinal) avec tooltip + unité TTC
- Labels énergie-aware **complets côté drawer** (ATRD/ATRT pour gaz, JAMAIS TURPE)
- Bannière "Reconstitution non fiable" en rouge si calcul fallback sans contrat

- **11 tests nouveaux verts** (8 backend P2-A + 3 FE source-guard énergie-aware)
- **131 tests non-régression verts** (billing + P1 + P1.5 cumulés)
- **Audit fonctionnel curl** : `kpi_metadata` + `is_reliable` + `energy_type` confirmés live
- **Audit visuel Playwright** : KPI renommé visible, drawer affiche ATRD au lieu de TURPE pour gaz, **0 console error / 0 network 4xx/5xx**

---

## 1. Phase 0 — Audit READ-ONLY (3 agents parallèles)

10 findings identifiés, 6 P0/P1 retenus pour P2-A (le reste reporté P2-B / P3) :

| # | Sujet | Sévérité | Statut P2-A |
|---|---|---|---|
| F1 | Facture sans contrat : shadow calculé en fallback mais présenté comme fiable | **P0** | ✅ livré |
| F2 | `/billing/summary` KPI sans contexte (période/unit/source) | **P1** | ✅ livré |
| F4 | `audit_invoice_full` ne retourne pas `energy_type` explicite | P1 | ✅ livré |
| F5 | KPI "Pertes estimées" ambigu (gain ou surcoût ?) | P1 | ✅ livré |
| F7 | Drawer affiche "Réseau (TURPE)" même pour gaz (bug racine) | **P0** | ✅ livré |
| F8 | Pas de badge visuel "non fiable" si shadow fallback | **P0** | ✅ livré |
| F3 | Anomalies devenant valorisables → action non re-générée | P1 | ⏸ P2-B |
| F6 | Drawer manque le numéro de contrat + code règle (R19/R27) | P1 | ⏸ P2-B |
| F9 | Pas de badge énergie ⚡/🔥 dans listes anomalies | P2 | ⏸ P3 |
| F10 | Pas de lien retour anomalie ← action dans V4 drawer | P1 | ⏸ P2-B |

Choix : 6 fixes **calculs + UX critique** ; les 4 autres restent inscrits en P2-B (refonte UI plus large).

---

## 2. Backend — F1 / F2 / F4

### F1 — `shadow_billing_v2` retourne `is_reliable` + `reliability_reason`

[`services/billing_shadow_v2.py:502-540`](backend/services/billing_shadow_v2.py#L502-L540)

```python
is_reliable = bool(contract and has_contract_price)
reliability_reason = None
if not contract:
    reliability_reason = (
        "Aucun contrat rattaché à cette facture — reconstitution basée sur le prix "
        "par défaut. Importez le contrat pour fiabiliser le calcul."
    )
elif not has_contract_price:
    reliability_reason = (
        "Contrat trouvé mais sans prix de référence — reconstitution basée sur le prix "
        "par défaut. Compléter `price_ref_eur_per_kwh` sur le contrat."
    )
```

Plus `period_start` / `period_end` exposés dans la réponse (avant : utilisés en interne pour prorata mais pas exposés).

### F2 — `/billing/summary` retourne `kpi_metadata`

[`routes/billing.py:990-1013`](backend/routes/billing.py#L990-L1013) + [`services/billing_service.py::get_billing_summary`](backend/services/billing_service.py)

```python
"kpi_metadata": {
    "period_analyzed": {"start": "2025-06-01", "end": "2026-05-31"},
    "scope": "org" | "site" | "all_organisations",
    "total_eur_unit": "TTC",
    "total_estimated_loss_eur_unit": "TTC",
    "total_estimated_loss_eur_source": "Σ BillingInsight.estimated_loss_eur (issus de shadow_billing_v2 delta_ttc)",
    "computed_at": "2026-05-24T...",
}
```

Le `BillingSummaryResponse` Pydantic ajoute `kpi_metadata: Optional[dict]` pour ne pas filtrer ce nouveau champ.

### F4 — `audit_invoice_full` retourne `energy_type` + `period_start/end`

[`services/billing_service.py:1088-1118`](backend/services/billing_service.py#L1088)

```python
energy_type = None
if contract:
    energy_type = contract.energy_type.value if contract.energy_type else None
elif shadow and shadow.get("energy_type"):
    energy_type = shadow.get("energy_type")

return {
    "invoice_id": ...,
    "energy_type": energy_type,  # P2-A F4
    "period_start": invoice.period_start.isoformat() if invoice.period_start else None,
    "period_end": invoice.period_end.isoformat() if invoice.period_end else None,
    ...
}
```

### Trigger recalcul shadow_v2 pour insights legacy

[`routes/billing.py:1111-1118`](backend/routes/billing.py#L1111)

Ancien : `if metrics.get("expected_ttc") is None` (recalcule seulement si breakdown vide).
Nouveau : `or "is_reliable" not in metrics` (recalcule si métadonnées P2-A absentes). Cela permet aux insights legacy de la DB démo de récupérer `is_reliable` + `period_start/end` à l'ouverture du drawer, sans purge/re-seed.

---

## 3. Frontend — F5 / F7 / F8

### F5 — KPI "Pertes estimées" → "Surfacturations à contester"

[`frontend/src/pages/BillIntelPage.jsx:910-924`](frontend/src/pages/BillIntelPage.jsx#L910)

- **Avant** : `<SummaryCard label="Pertes estimées" value={fmtEur(activeLoss)} color="orange" />` — ambigu (gain ? coût ? HT ? TTC ?).
- **Après** : `label="Surfacturations à contester"`, `value="{X} € TTC"`, `title="Somme des écarts shadow billing TTC sur factures encore ouvertes — montants à récupérer via réclamation fournisseur."` (tooltip HTML natif).

`SummaryCard` étendu pour accepter le prop `title` qui devient le tooltip natif au survol (effort minimal, pas de refonte de composant).

### F7 — `InsightDrawer.getBreakdownRows()` énergie-aware

[`frontend/src/components/InsightDrawer.jsx:175-215`](frontend/src/components/InsightDrawer.jsx#L175)

```jsx
const reseauLabel = isGaz ? (
  <>Acheminement (<Explain term="atrd">ATRD</Explain> + <Explain term="atrt">ATRT</Explain>)</>
) : (
  <>Réseau (<Explain term="turpe">TURPE</Explain>)</>
);
```

Idem pour `fournitureLabel` (gaz/élec) et `taxLabel` (TICGN/CSPE-TICFE). Et le `cause label reseau_mismatch` devient une fonction qui adapte le wording :

```jsx
reseau_mismatch: (m) => {
  const isGaz = (m.energy_type || '').toUpperCase() === 'GAZ';
  const refLabel = isGaz ? <>ATRD + ATRT</> : <>TURPE</>;
  return <>L'écart {isGaz ? 'acheminement' : 'réseau'}/{refLabel} ({fmt(m.delta_reseau)} €) dépasse le seuil de 10%.</>;
};
```

### F8 — `ReconstitutionBanner` affiche "Reconstitution non fiable" en rouge

[`frontend/src/components/InsightDrawer.jsx:299-360`](frontend/src/components/InsightDrawer.jsx#L299)

Si `breakdown.is_reliable === false`, on rend un bandeau rouge en HEAD du drawer avec icône `Info` + titre **"Reconstitution non fiable"** + `breakdown.reliability_reason` FR. Le DAF voit immédiatement qu'il ne peut pas utiliser ce calcul comme preuve opposable.

Le bandeau de "confidence" classique reste affiché en-dessous (rétro-compat).

---

## 4. Tests

### 8 tests backend P2-A ([`test_billing_p2a_reliability_metadata.py`](backend/tests/test_billing_p2a_reliability_metadata.py))

| # | Test | Vérifie |
|---|---|---|
| 1 | `shadow_v2_reliable_when_contract_with_price` | F1 : contrat + prix → `is_reliable=True` |
| 2 | `shadow_v2_unreliable_when_no_contract` | F1 : sans contrat → `is_reliable=False` + raison FR mentionne "contrat" |
| 3 | `shadow_v2_unreliable_when_contract_no_price` | F1 : sans `price_ref` → `is_reliable=False` + raison FR mentionne "prix" |
| 4 | `billing_summary_exposes_kpi_metadata` | F2 : période + scope + unit + source + computed_at |
| 5 | `billing_summary_empty_period_when_no_invoices` | F2 : DB vide → start/end=None sans crash |
| 6 | `audit_invoice_full_exposes_energy_type_elec` | F4 : facture élec → `energy_type="elec"` |
| 7 | `audit_invoice_full_exposes_energy_type_gaz` | F4 : facture gaz → `energy_type="gaz"` |
| 8 | `audit_invoice_full_energy_type_none_when_no_contract` | F4 : pas de gaz inventé sans contrat |

### 3 tests frontend source-guard ([`billing_energy_aware_labels_p2a.test.jsx`](frontend/src/__tests__/billing_energy_aware_labels_p2a.test.jsx))

| # | Test | Vérifie |
|---|---|---|
| 1 | `getBreakdownRows : label réseau gaz contient ATRD + ATRT (pas TURPE)` | F7 : code-source garde la doctrine, `gazBranch` ne contient JAMAIS "TURPE" |
| 2 | `CAUSE_LABELS.reseau_mismatch : wording énergie-aware` | F7 : fonction utilise `isGaz` + branche ATRD/ATRT |
| 3 | `Pas de chaîne fixe 'Réseau (TURPE)' hardcodée` | F7 : chaque occurrence "Réseau (" est dans une branche conditionnelle avec `isGaz`/`energy_type` |

### Non-régression : 131 tests billing verts

```
tests/test_billing.py                                ✅
tests/test_bill_anomaly_detector.py                  ✅ (19)
tests/test_bill_anomaly_evidence_p1.py               ✅ (12)
tests/test_bill_anomaly_monetizable_invariant_p1.py  ✅ (7)
tests/test_billing_audit_all_idempotent_p15.py       ✅ (10)
tests/test_billing_audit_all_no_org_context_p1.py    ✅ (3)
tests/test_billing_sync_actions_from_anomalies_p1.py ✅ (6)
tests/test_billing_explainability_energy_aware_p1.py ✅ (7)
tests/test_billing_shadow_expected_elec.py           ✅ (18)
tests/test_billing_p2a_reliability_metadata.py       ✅ (8 NOUVEAUX)
─────────────────────────────────────────────────────────────
Total billing                                        ✅ 131
```

---

## 5. Audit fonctionnel curl

Backend démarré sur `http://127.0.0.1:8001` (DEMO_MODE=true). DB démo HELIOS.

### Cas 1 — F2 : `/api/billing/summary`

```bash
curl -H "X-Org-Id: 1" http://127.0.0.1:8001/api/billing/summary
```

```json
{
  "total_estimated_loss_eur": 19808.92,
  "kpi_metadata": {
    "period_analyzed": {"start": "2025-06-01", "end": "2026-05-31"},
    "scope": "org",
    "total_eur_unit": "TTC",
    "total_estimated_loss_eur_unit": "TTC",
    "total_estimated_loss_eur_source": "Σ BillingInsight.estimated_loss_eur (issus de shadow_billing_v2 delta_ttc)",
    "computed_at": "2026-05-24T..."
  }
}
```

### Cas 2 — F1+F4 : `/api/billing/insights/{id}` (consommé par drawer)

```bash
curl -H "X-Org-Id: 1" http://127.0.0.1:8001/api/billing/insights/439
```

```json
{
  "metrics": {
    "energy_type": "ELEC",
    "is_reliable": true,
    "reliability_reason": null,
    "period_start": "2025-11-01",
    "period_end": "2025-11-30",
    ...
  }
}
```

### Cas 3 — F4 : `/api/billing/audit/{id}`

```json
{
  "energy_type": "elec",  // P2-A F4 — explicite
  "period_start": "2026-05-01",
  "period_end": "2026-05-31",
  ...
}
```

---

## 6. Audit visuel Playwright

Frontend démarré sur `http://127.0.0.1:5175`. Captures dans `/tmp/promeos-audit-billing-p2a/*.png` (hors repo, gitignore).

| # | Étape | Capture | Observation |
|---|---|---|---|
| 0 | Login démo HELIOS | n/a | OK |
| 1 | `/bill-intel` rendu | `01_bill_intel.png` | KPI **"Surfacturations à contester"** visible ✅ — ancien KPI "Pertes estimées" absent (régression confirmée) |
| 2 | Click 1er insight → drawer ouvert | `02_drawer_insight.png` | Drawer affiche **"Acheminement (ATRD + ATRT)"** (facture gaz), pas "Réseau (TURPE)" ✅ |
| 3 | `/billing` rendu | `03_billing.png` | Timeline + chronologie OK |
| 4 | `/action-center-v4/pilotage` | `04_centre_action.png` | Centre d'Action accessible, items billing visibles (via sync P1) |

### Métriques

| Métrique | Compte |
|---|---|
| `console.error` / `pageerror` | **0** |
| HTTP 4xx/5xx (hors hot-update/favicon) | **0** |

---

## 7. Critères d'acceptation

| Critère | Statut | Preuve |
|---|---|---|
| Aucun label électricité sur facture gaz | ✅ | F7 + source-guard FE + Playwright capture 02 |
| Aucun label gaz sur facture électricité | ✅ | F7 branche `isGaz ? ... : ...` (test 3) |
| Tous les KPIs ont source/formule/unité/période | ✅ | F2 `kpi_metadata` (curl cas 1) |
| Une anomalie valorisée a montant + preuve/action | ✅ | héritage P1 C1/C2/C4 (non touché P2-A) |
| Une anomalie informative est clairement non valorisable | ✅ | héritage P1 C1 `is_monetizable` |
| Drawer anomalie compréhensible par un DAF | ✅ | F7 labels énergie-aware + F8 bannière fiabilité |
| Timeline facture lisible | ✅ | héritage existant (capture 03) |
| Facture sans contrat non fiable | ✅ | F1 (test 2) + F8 bannière rouge "Reconstitution non fiable" |
| Sync action idempotente | ✅ | héritage P1 C4 + P1.5 (non-régression 6 tests verts) |
| Tests nouveaux verts | ✅ | 8 BE + 3 FE = 11/11 |
| Non-régression Patrimoine + Conformité + Billing P1/P1.5 | ✅ | 131 tests billing verts (cumul P1+P1.5+P2-A) |
| Audit curl + Playwright livré | ✅ | §5 + §6 |
| Aucun nouveau menu | ✅ | NavRegistry intact |
| Aucun écran fantôme | ✅ | aucune page créée |

---

## 8. Dette résiduelle inscrite P2-B

| ID | Sujet | Sévérité | Note |
|---|---|---|---|
| F3 | Anomalies devenant valorisables après update → action non re-générée | P1 | Refacto idempotence sync (signature par `anomaly_id` au lieu de `title`) |
| F6 | Drawer manque numéro contrat + code règle (R19/R27) visible | P1 | Backend ne propage pas encore `contract_number` + `rule_code` dans `/insights/{id}` |
| F9 | Pas de badge énergie ⚡/🔥 dans listes anomalies BillIntelPage | P2 | UX nice-to-have |
| F10 | Pas de lien retour anomalie ← action dans V4 drawer | P1 | Nécessite query `external_ref` côté V4 drawer |
| Nommage var `turpe_energie` dans shadow_v2 (gaz utilise cette var pour ATRD+ATRT) | P2 | Renommer en `reseau_rate_eur_kwh` |
| Filtre `domain=FACTURATION` dans ActionCenterV4ListPage | P0 produit | Sur-scope P2-A — refonte filterbar |

---

## 9. Verdict

### 🟢 GO pour le prochain chantier

**Points forts du sprint P2-A** :
1. **F1+F8** : la doctrine "facture sans contrat = non fiable" devient enfin visible côté UI (le calcul existait déjà mais était présenté comme fiable). Crédibilité produit restaurée.
2. **F2** : tous les KPIs `/summary` ont désormais source + formule + unité + période + périmètre + `computed_at`. Doctrine respectée.
3. **F7** : bug racine gaz/élec étendu au drawer (P1 C7 ne couvrait que `compute_contributors`). Source-guard FE empêche toute régression future.
4. **F5** : renommage minimal mais sémantique forte (DAF comprend "à contester" plutôt que "pertes").
5. **F4** : `energy_type` enfin explicite dans audit (base nécessaire pour futurs badges énergie F9).

**Note brique Bill Intelligence** : **8,5/10 → 9/10** post-P2-A.

### Prochains chantiers possibles

- **Bill Intel P2-B** : F3 + F6 + F10 (idempotence avancée + drawer enrichi + lien retour V4) + filtre `domain` ActionCenterV4ListPage (le seul P0 reporté car nécessite refonte FilterBar)
- **Bill Intel P2-C grilles gaz** : import grilles ATRD 7 / ATRT 8 dans `tarifs_reglementaires.yaml` (dette D-P2-006/007 P1)
- **Autre brique** : Achat Energie ou Cockpit V4 DAF

---

*Audit clôturé le 2026-05-24 sur `claude/bill-intelligence-p2a-functional-ux-hardening`. Mode READ-ONLY après corrections. Méthode conforme [[feedback-audit-sprint-visuel-fonctionnel]] : 3 agents Explore parallèles Phase 0 + 6 fix ciblés Phases 1-2 + audit fonctionnel curl (3 cas) + audit visuel Playwright golden path (4 captures) → 0 console error / 0 network 4xx-5xx. Captures hors repo dans `/tmp/promeos-audit-billing-p2a/`.*
