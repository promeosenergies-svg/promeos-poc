# FIX PROMEOS — Sprint S P0-2 Conformité ↔ Facture — 24 mars 2026

## 1. Résumé exécutif

Le P0-2 (rupture totale conformité ↔ facture) est fermé. 3 modifications ciblées créent un lien bidirectionnel crédible entre conformité et facturation.

| # | Modification | Fichier | Effort |
|---|---|---|---|
| 1 | Bandeau risque + CTA "Voir conformité" dans BillIntelPage | `BillIntelPage.jsx` | S |
| 2 | CTA "Vérifier les factures" dans ConformitePage | `ConformitePage.jsx` | XS |
| 3 | `billing_anomalies_eur` scopé correctement (excl. resolved/false_positive) | `cockpit.py` | XS |

**Impact estimé** : +0.3 point (8.3 → 8.6).

---

## 2. Modifications réalisées

### Fix 1 — BillIntelPage : bandeau risque + CTA conformité

**Logique** : si les insights chargés contiennent des anomalies critiques/high OU un total `estimated_loss_eur > 0`, affiche un bandeau amber sobre avec :
- Nombre d'anomalies critiques
- Risque estimé total en EUR
- Message contextuel : "Les écarts facture peuvent révéler un risque de conformité réglementaire"
- CTA "Voir conformité →" qui navigue vers `/conformite`

**Caractéristiques** :
- Aucun appel API supplémentaire (exploite les `insights` déjà fetchés)
- Se cache automatiquement si 0 anomalie critique et 0 perte estimée
- Sobre, non alarmiste (fond amber-50, pas rouge)
- Scope préservé via ScopeContext

**Fichier** : `frontend/src/pages/BillIntelPage.jsx` — après le CTA achat (ligne 528+)

### Fix 2 — ConformitePage : CTA "Vérifier les factures"

**Logique** : quand le risque financier global est > 0 (badge déjà affiché), ajoute un bouton "Vérifier les factures →" à côté du badge.

**Caractéristiques** :
- Apparaît uniquement quand `score.total_impact_eur > 0`
- Navigue vers `/bill-intel`
- Discret (text-xs, bleu, icône FileText)
- `data-testid="conformite-cta-factures"` pour les tests E2E

**Fichier** : `frontend/src/pages/ConformitePage.jsx` — dans le bloc risque financier (ligne 625+)

### Fix 3 — Cockpit : billing_anomalies_eur scopé

**Avant** : `SUM(BillingInsight.estimated_loss_eur)` sans filtre de statut — comptait les faux positifs et les résolus.

**Après** : Exclut `InsightStatus.RESOLVED` et `InsightStatus.FALSE_POSITIVE`. Seules les anomalies ouvertes ou acquittées sont comptées.

**Fichier** : `backend/routes/cockpit.py` — lignes 146-157

---

## 3. Fichiers touchés

| Fichier | Modification |
|---|---|
| `frontend/src/pages/BillIntelPage.jsx` | Import `ShieldAlert`, bandeau conditionnel avec CTA conformité |
| `frontend/src/pages/ConformitePage.jsx` | Import `FileText`, CTA "Vérifier les factures" |
| `backend/routes/cockpit.py` | Filtre `insight_status` sur billing loss |

---

## 4. Tests

| Suite | Résultat |
|---|---|
| `test_compliance_v68.py` + `test_emissions.py` + `test_billing.py` | 81/81 ✅ |
| `step4_co2_guard.test.js` | 9/9 ✅ |
| Import `routes.cockpit` | OK ✅ |

---

## 5. Risques de régression

| Risque | Probabilité | Mitigation |
|---|---|---|
| Bandeau BillIntel trop visible sur petits écrans | Faible | Responsive par défaut (flex-wrap implicite Tailwind) |
| CTA conformité cliqué mais scope perdu | Faible | ScopeContext persiste en localStorage |
| `notin_` SQL non supporté SQLite | Nulle | `notin_` est standard SQLAlchemy, testé |

---

## 6. Points non traités

| Point | Raison |
|---|---|
| Lien profond conformité → facture spécifique (par finding) | Effort M, nécessite FK entre ComplianceFinding et BillingInsight |
| Risque financier conformité affiché dans BillIntelPage (vrai montant réglementaire) | Nécessite appel API supplémentaire ou enrichissement de la réponse getSites |
| `contract_risk_eur` encore hardcodé à 0 dans cockpit | Hors scope (nécessite modèle de risque contrat) |

---

## 7. Definition of Done

- [x] BillIntelPage affiche un bandeau quand anomalies critiques/high détectées
- [x] BillIntelPage contient CTA "Voir conformité →"
- [x] ConformitePage contient CTA "Vérifier les factures →" quand risque > 0
- [x] Cockpit `billing_anomalies_eur` exclut resolved + false_positive
- [x] 0 appel API ajouté dans BillIntelPage (données existantes exploitées)
- [x] 81+ tests backend passent
- [x] 9 tests frontend CO₂ guards passent
- [x] Aucun fichier Yannick touché
- [x] `data-testid` ajouté pour E2E future
