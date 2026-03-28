# AUDIT PROMEOS — ÉTAPE 3 : BILL INTELLIGENCE & ACHAT

> **Date** : 2026-03-23
> **Baseline** : Étapes 0, 1, 2
> **Méthode** : Lecture exhaustive des moteurs billing + purchase, vérification formules/taux aux sources officielles (×2 par point sensible)
> **Statut** : AUDIT UNIQUEMENT — aucune modification du repo

---

## 1. Résumé exécutif

**Bill Intelligence est le 2e meilleur asset du POC après BACS.** Le moteur de reconstitution facture V2 est impressionnant : TURPE 7 composant par composant (gestion, comptage, soutirage fixe/variable × 4 plages), accise versionnée (2023→2026, vérifiée Légifrance), TVA différenciée (5.5%/20%), prorata calendaire exact, 14 règles anomalie + 20 règles audit structurées.

**L'Achat a un double moteur** : un moteur "grand public" (3 scénarios × facteurs fixes 1.05/0.95/0.88) ET un moteur avancé (4 stratégies market-based avec forward, spread, volatility bands, profil RéFlex solaire). Le moteur avancé est **significativement plus crédible** que l'audit initial ne le laissait croire.

**Verdict par brique :**

| Brique | Note | Justification |
| --- | --- | --- |
| Reconstitution facture V2 | **8/10** | TURPE 7 réel, accise versionnée, TVA 5.5/20%, prorata exact, segments C4/C5/C3 |
| Anomaly engine (14 règles) | **7.5/10** | Règles crédibles, seuils documentés, dédup intelligente (R1 inhibe R10/R13/R14) |
| Audit rules V0 (20 règles) | **7/10** | Contrôles comptables solides (somme HT, TTC=HT+TVA, prix crédible) |
| Scénarios achat grand public | **4/10** | Facteurs prix fixes (1.05/0.95/0.88), pas de données marché |
| Scénarios achat avancé | **7/10** | Forward + spread + volatility + profil RéFlex, mais données marché = seed |
| Lien facture→achat→actions | **5.5/10** | Volume kWh réel, CTA croisés existent, mais actions éphémères |

---

## 2. Cartographie réelle Bill Intelligence

```text
                    ARCHITECTURE BILLING PROMEOS
                    ============================

[CSV/PDF Import]──→[EnergyInvoice]──→[EnergyInvoiceLine]
                        │                    │
                        │                    ▼
                        │            [ConceptAllocation]
                        │            (fourniture/acheminement/taxes/tva/abonnement)
                        │
                        ▼
              ┌─────────────────────────────────────────┐
              │  14 ANOMALY RULES (billing_service.py)  │
              │  R1:  Shadow gap > 20%                  │
              │  R2:  Unit price > 0.30€/kWh            │
              │  R3:  Duplicate invoice                 │
              │  R4:  Missing period                    │
              │  R5:  Period > 62 days                  │
              │  R6:  Negative kWh                      │
              │  R7:  Zero amount                       │
              │  R8:  Lines sum ≠ total (> 2%)          │
              │  R9:  Consumption spike > 2× avg        │
              │  R10: Price drift > 15% vs contract     │
              │  R11: TTC ≠ HT+TVA (> 2% or 5€)        │
              │  R12: Contract expiry < 90 days         │
              │  R13: Réseau/TURPE mismatch > 15%       │
              │  R14: Taxes/CSPE mismatch > 10%         │
              └────────────────┬────────────────────────┘
                               │
                               ▼
                      [BillingInsight]
                      type, severity, estimated_loss_eur
                      insight_status: open→ack→resolved
                               │
                               ▼
              ┌─────────────────────────────────────────┐
              │  20 AUDIT RULES (audit_rules_v0.py)     │
              │  R01: Σ composantes ≠ total HT          │
              │  R02: TTC ≠ HT + TVA                    │
              │  R03: TVA taux incorrect par composante  │
              │  ...R04-R20...                          │
              │  R15: Facture sans composante (CRITICAL) │
              │  R19: Pénalité/dépassement              │
              │  R20: Montant > 50 000€                 │
              └─────────────────────────────────────────┘

              ┌─────────────────────────────────────────┐
              │  ENGINE V2 (billing_engine/)             │
              │  Reconstitution composant par composant  │
              │  ├── Fourniture (per period pricing)     │
              │  ├── TURPE (gestion+comptage+soutirage)  │
              │  ├── Accise (versionnée 2023→2026)       │
              │  ├── CTA                                │
              │  └── TVA (5.5% abo / 20% énergie)       │
              │  Segments: C4 BT, C5 BT, C3 HTA         │
              │  Prorata: calendar-exact (days/year)     │
              │  Output: ReconstitutionResult            │
              └─────────────────────────────────────────┘
```

---

## 3. Cartographie réelle Achat

```text
              ┌─────────────────────────────────────────┐
              │  MOTEUR GRAND PUBLIC (V99)               │
              │  purchase_scenarios_service.py           │
              │  3 scénarios × price_factor fixe         │
              │  A: Fixe × 1.05                         │
              │  B: Indexé × 0.95                       │
              │  C: Spot × 0.88                         │
              │  Volume: Σ(EnergyInvoice.energy_kwh)    │
              │  Coût: price_ref × factor × annual_kwh  │
              └─────────────────────────────────────────┘

              ┌─────────────────────────────────────────┐
              │  MOTEUR AVANCÉ                           │
              │  purchase_service.py + purchase_pricing  │
              │  4 stratégies market-based :             │
              │  FIXE:   forward + terme + margin 2.5€  │
              │  INDEXE: spot + spread 4.0€/MWh         │
              │  SPOT:   spot × profile + fee 1.5€      │
              │  REFLEX: blocs horaires × multiplicat.  │
              │  + scoring (risk × budget × green)      │
              │  + recommendation algorithm             │
              │  + volatility bands (p10/p90)           │
              │  + persistance (PurchaseScenarioResult)  │
              └─────────────────────────────────────────┘

              ┌─────────────────────────────────────────┐
              │  ACTIONS ENGINE (éphémère)               │
              │  purchase_actions_engine.py              │
              │  5 types: renewal_urgent/soon/plan,      │
              │           strategy_switch, accept_reco   │
              │  Persisté UNIQUEMENT via sync_actions()  │
              └─────────────────────────────────────────┘
```

**DÉCOUVERTE** : L'audit initial parlait uniquement du moteur "grand public" (3 facteurs fixes). En réalité, un moteur avancé (`purchase_service.py` + `purchase_pricing.py`) existe avec 4 stratégies market-based, forward pricing, volatility bands, profil RéFlex solaire et algorithme de recommandation.

**Tag** : PARTIEL — Le moteur avancé est implémenté mais dépend de données marché seed (pas de feed EPEX Spot réel)

---

## 4. Décomposition des coûts et formules

### 4.1 Shadow billing — formule core

```python
# billing_service.py:162
shadow_total = energy_kwh × price_ref    # HT, EUR
delta_eur = actual_total - shadow_total
delta_pct = (delta_eur / shadow_total) × 100
```

**Prix de référence** — chaîne de priorité (`billing_service.py:47-115`) :

| Priorité | Source | Détail | Fichier:ligne |
| --- | --- | --- | --- |
| 1 | Contrat actif | `EnergyContract.price_ref_eur_per_kwh` avec overlap période | `:62-82` |
| 2 | Prix marché EPEX | `AVG(MarketPrice.price_eur_mwh) / 1000` sur 30 jours | `:84-105` |
| 3 | Profil tarifaire site | `SiteTariffProfile.price_ref_eur_per_kwh` | `:107-110` |
| 4 | Fallback défaut | env `PROMEOS_DEFAULT_PRICE_ELEC` (0.15) ou `PROMEOS_DEFAULT_PRICE_GAZ` (0.08) | `:112-115` |

### 4.2 Reconstitution V2 — composants

Le billing engine V2 reconstitue **composant par composant** :

| Composant | Formule | Taux TVA | Source taux |
| --- | --- | --- | --- |
| **Gestion** | `TURPE_GESTION_C4 × prorata` (217.80 EUR/an) | 5.5% | CRE n°2025-78 p.13 |
| **Comptage** | `TURPE_COMPTAGE_C4 × prorata` (283.27 EUR/an) | 5.5% | CRE n°2025-78 p.13 |
| **Soutirage fixe** | `b_i × kVA × prorata` (4 plages HPH/HCH/HPB/HCB) | 5.5% | CRE n°2025-78 p.14 |
| **Soutirage variable** | `c_i × kWh` (4 plages) | 20% | CRE n°2025-78 p.15 |
| **Fourniture** | `prix_par_période × kWh_par_période` | 20% | Contrat |
| **Accise** | Versionnée (voir §9) | 20% | Loi de finances |
| **CTA** | Taux fixe × TURPE fixe | 5.5% | CRE |

**Prorata** : `days_in_period / days_in_year` (calendar-exact, leap year aware) — `engine.py:58-72`

**Segments supportés** : C4 BT (>36 kVA), C5 BT (≤36 kVA), C3 HTA (>250 kVA)

**Tag** : IMPLÉMENTÉ — Reconstitution réelle, pas une estimation simplifiée

### 4.3 Incohérence prix par défaut

| Source | Élec | Gaz | Fichier |
| --- | --- | --- | --- |
| `config/default_prices.py:10-11` | **0.18** EUR/kWh | **0.09** EUR/kWh | Hardcodé |
| `billing_service.py:43-44` | **0.15** EUR/kWh | **0.08** EUR/kWh | Env var fallback |
| `billing_shadow_v2.py` | 0.0453 EUR/kWh (TURPE seul) | — | Composant réseau |

**Impact** : Quand contrat/marché/tarif tous absents, `get_reference_price()` retourne 0.15 (env), mais `config/default_prices.py` dit 0.18. Le shadow billing utilise un prix inférieur de 17% au prix configuré.

**Tag** : À RISQUE CRÉDIBILITÉ — Deux sources incohérentes

---

## 5. Shadow billing / anomalies / écarts

### 5.1 Les 14 règles anomalie — détail et seuils

| Rule | Seuil | Sévérité | Données requises | Traçable ? |
| --- | --- | --- | --- | --- |
| R1 Shadow gap | > 20% delta | HIGH | kWh + total_eur + prix_ref | ✅ inputs + threshold + confidence dans metrics_json |
| R2 Prix unitaire élevé | > 0.30 €/kWh (elec) / 0.15 (gaz) | MEDIUM | total_eur / energy_kwh | ✅ |
| R3 Doublon facture | Même (site, période, montant) | HIGH | Multi-facture query | ✅ |
| R4 Période manquante | period_start ou period_end null | MEDIUM | Invoice fields | ✅ |
| R5 Période trop longue | > 62 jours | LOW | period_end − period_start | ✅ |
| R6 kWh négatifs | energy_kwh < 0 | HIGH | Invoice field | ✅ |
| R7 Montant zéro | total_eur = 0 avec kWh > 0 | MEDIUM | 2 fields | ✅ |
| R8 Σ lignes ≠ total | > 2% écart | MEDIUM | Invoice lines query | ✅ |
| R9 Pic consommation | > 2× moyenne 6 mois | HIGH | Historique site | ✅ + cross-link diagnostic-conso |
| R10 Dérive prix | > 15% vs contrat | MEDIUM/HIGH | Contract price + implied price | ✅ |
| R11 Cohérence TTC | > 2% ou > 5€ | MEDIUM | HT + TVA + TTC | ✅ |
| R12 Contrat expiré | < 90 jours ou dépassé | HIGH | Contract.end_date | ✅ |
| R13 Réseau/TURPE | > 15% delta vs reconstitution V2 | MEDIUM/HIGH | Shadow V2 réseau | ✅ |
| R14 Taxes/accise | > 10% delta vs reconstitution V2 | MEDIUM | Shadow V2 taxes | ✅ |

**Déduplication intelligente** (`billing_service.py:728-748`) : Quand R1 (shadow gap) se déclenche, R10 (price drift), R13 (réseau) et R14 (taxes) sont inhibées pour éviter de stacker 4 anomalies sur la même facture.

**Tag** : IMPLÉMENTÉ — Règles crédibles, seuils documentés, traçabilité complète

### 5.2 Les 20 règles audit V0

Les règles V0 (`app/bill_intelligence/rules/audit_rules_v0.py`) sont des **contrôles comptables** sur la structure interne d'une facture décomposée en composantes :

| Règle | Contrôle | Sévérité |
| --- | --- | --- |
| R01 | Σ composantes HT ≠ total HT (tolérance 0.02€) | ERROR |
| R02 | TTC ≠ HT + TVA | ERROR |
| R03 | TVA taux incorrect par composante (5.5% abo, 20% énergie) | ERROR |
| R05 | qty × unit_price ≠ amount_ht | WARNING |
| R07 | Composante accise ou CTA absente | WARNING |
| R13 | Prix unitaire hors plage crédible [0.01–1.00 €/kWh] | WARNING |
| R15 | Facture sans composante | CRITICAL |
| R19 | Pénalité/dépassement puissance détecté | WARNING |
| R20 | Montant total > 50 000€ | INFO |

**Tag** : IMPLÉMENTÉ — Contrôles comptables pertinents pour un audit facture B2B

### 5.3 Explainabilité des écarts

L'utilisateur peut comprendre un écart via :
- **InsightDrawer** (`components/InsightDrawer.jsx:547L`) : tableau Facturé vs Attendu par composante (fourniture, réseau, taxes, TVA, Total TTC)
- **Top Contributors** : graphe barres montrant les principaux drivers de l'écart
- **ShadowBreakdownCard** (`components/billing/ShadowBreakdownCard.jsx:283L`) : reconstitution déterministe avec formules, sources taux, hypothèses, warnings
- **Expert mode** : rule_id, method, energy_type, price_ref, kWh, threshold_pct, price_source, catalog_trace

**Tag** : IMPLÉMENTÉ — Explainabilité crédible pour un energy manager

---

## 6. Scénarios achat et hypothèses

### 6.1 Moteur grand public (V99) — facteurs fixes

```python
# purchase_scenarios_service.py:160
estimate_eur = price_ref × price_factor × annual_kwh
```

| Scénario | Factor | Écart vs ref |
| --- | --- | --- |
| A (Fixe) | 1.05 | +5% toujours |
| B (Indexé) | 0.95 | −5% toujours |
| C (Spot) | 0.88 | −12% toujours |

**Tag** : PLACEHOLDER — Écarts constants, détectables par un DAF

### 6.2 Moteur avancé — market-based

Le moteur avancé (`purchase_service.py` + `purchase_pricing.py`) est **significativement plus crédible** :

| Stratégie | Formule prix | Volatility bands | Risk score |
| --- | --- | --- | --- |
| FIXE | `forward × (1 + terme_premium%) + margin 2.5€/MWh` | ±1.0σ | 10–34 |
| INDEXE | `spot + spread 4.0€/MWh` | ±1.3σ | 35–55+ |
| SPOT | `spot × profile_factor + fee 1.5€/MWh` | ±1.6σ | 60–80+ |
| REFLEX | Blocs horaires (solaire été 0.72, pointe hiver 1.25, HC 0.80) + fee 2.0€/MWh | ±1.2σ | 40–65+ |

**Scoring recommandation** (`purchase_service.py:334`) :
```python
score = (1 − budget_priority) × safety_score + budget_priority × savings_norm
# + 5 pts bonus green si green_preference AND stratégie verte
```

**Données marché** : `MarketPrice` table alimentée par seed (`source: "Seed PROMEOS — basé sur tendances EPEX 2024-2025"`). **Pas de feed EPEX Spot réel.**

Defaults si aucune donnée marché : spot_30d = 68.0, spot_12m = 72.0, volatility = 15.0 EUR/MWh.

**Tag** : PARTIEL — Moteur crédible mais données = seed. Prêt pour données réelles.

### 6.3 Profil RéFlex solaire

Le moteur RéFlex (`purchase_service.py:149-205`) modélise 6 blocs horaires avec multiplicateurs de prix et report de charge :

| Bloc | Période | Heures | Multiplicateur | Poids annuel |
| --- | --- | --- | --- | --- |
| solaire_ete_sem | Avr–Sep, L–V | 13–16h | 0.72 | 8% |
| solaire_ete_we | Avr–Sep, S–D | 10–17h | 0.68 | 4% |
| pointe_hiver_matin | Jan–Mar+Oct–Dec, L–V | 8–10h | 1.25 | 6% |
| pointe_hiver_soir | Jan–Mar+Oct–Dec, L–V | 17–20h | 1.25 | 6% |
| HC | Toute année | 0–6h | 0.80 | 25% |
| HP | Toute année | 6–22h | 1.00 | 51% |

**Report de charge** : Slider 0–100% déplace des kWh HP vers solaire_ete (prix plus bas). Effort score = `min(80, 20 + report_pct × 400)`.

**Tag** : IMPLÉMENTÉ — Modèle horaire crédible pour un POC. Les multiplicateurs sont des hypothèses raisonnables.

---

## 7. Liens facture → achat → actions

### 7.1 Facture → Achat

| Donnée | Circule ? | Source → Destination | Fichier:ligne |
| --- | --- | --- | --- |
| Volume annuel kWh | **OUI** | `EnergyInvoice.energy_kwh` → `estimate_consumption()` → `PurchaseAssumptionSet.volume_kwh_an` | `purchase_service.py:74-96` |
| Prix de référence contrat | **OUI** | `EnergyContract.price_ref_eur_per_kwh` → scénarios | `purchase_scenarios_service.py:138` |
| Profil HP/HC | **NON** | Non utilisé dans les scénarios simples | — |
| Saisonnalité | **PARTIEL** | Modélisée dans RéFlex, pas dans fixe/indexé/spot | `purchase_service.py:130-135` |
| Anomalies facture | **NON** | Pas de lien direct billing insight → purchase scenario | — |

### 7.2 Achat → Actions

| Étape | Implémenté ? | Fichier:ligne |
| --- | --- | --- |
| Calcul 5 types actions | **OUI** | `purchase_actions_engine.py:30-206` |
| Persistance automatique | **NON** — éphémère par défaut | Actions recalculées à chaque `GET /api/purchase/actions` |
| Persistance via sync | **OUI** (manuel) | `action_hub_service.py:302-307` via `POST /api/actions/sync` |
| source_type = PURCHASE | **OUI** | `action_item.py:34-42` |
| Filtrage UI par source | **OUI** | `ActionsPage.jsx:561` → `?source=purchase` |
| Cap par org | **OUI** — max 6 | `action_hub_service.py:284` |
| Acceptation scénario | **OUI** | `PATCH /purchase/results/{id}/accept` → `reco_status: DRAFT→ACCEPTED` |

### 7.3 Navigation croisée

| Depuis | Vers | CTA | Fichier:ligne |
| --- | --- | --- | --- |
| BillIntelPage | PurchasePage | "Optimiser l'achat énergie" → `/achat` | `BillIntelPage.jsx:529-534` |
| PurchasePage | BillIntelPage | "Contrôler facture" → `toBillIntel({site_id, month})` | `PurchasePage.jsx:1254-1260` |
| PurchasePage | BillIntelPage | "Voir les factures" (renewal) → `toBillIntel({site_id})` | `PurchasePage.jsx:1654` |
| Site360 factures | PurchaseAssistant | "Créer scénario d'achat" → `/achat-assistant?site_id=X` | `Site360.jsx:1510` |
| Site360 factures | BillingPage | "Voir timeline complète" → `/billing?site_id=X` | `Site360.jsx:1515` |
| **ConformitePage** | **BillIntelPage** | **AUCUN** | — |
| **BillIntelPage** | **ConformitePage** | **AUCUN** | — |

**Tag** : PARTIEL — Liens billing↔purchase fonctionnels. Liens conformité↔billing toujours cassés (étape 1 confirmé).

---

## 8. KPI ou vues trompeuses

### B1 : Deux moteurs achat coexistent silencieusement

Le moteur grand public (3 facteurs fixes) est appelé par `GET /api/purchase/scenarios?contract_id=X`. Le moteur avancé (4 stratégies market-based) est appelé par `POST /api/purchase/compute/{site_id}`. L'UI PurchasePage utilise le moteur **avancé**. L'UI PurchaseAssistantPage a son propre engine JS (déterministe, pas d'appel API).

**Risque** : Si un développeur ou un démonstrateur appelle le mauvais endpoint, les résultats seront radicalement différents.

**Tag** : IMPLICITE MAIS NON FIABILISÉ

### B2 : Données marché = seed

Toutes les données `MarketPrice` sont seedées (`source: "Seed PROMEOS — basé sur tendances EPEX 2024-2025"`). Les fallback defaults sont spot_30d = 68.0, spot_12m = 72.0, volatility = 15.0.

Un energy manager qui compare les prix affichés aux cours réels EPEX détectera immédiatement la divergence si les marchés ont bougé.

**Tag** : À RISQUE CRÉDIBILITÉ en démo marché

### B3 : Shadow billing simplifié (V1) vs reconstitution (V2)

Deux niveaux de shadow billing coexistent :
- **V1** : `energy_kwh × price_ref` (une multiplication)
- **V2** : Reconstitution composant par composant (TURPE + accise + fourniture + TVA)

R1 (shadow gap) utilise V1 par défaut, puis enrichit avec V2 si disponible. R13 et R14 utilisent V2. L'UI `ShadowBreakdownCard` distingue les deux avec un badge (RECONSTITUTED / confidence).

**Risque** : Si V2 échoue (données manquantes), le fallback V1 peut produire des écarts différents.

**Tag** : IMPLÉMENTÉ mais avec fallback dégradé

### B4 : PurchaseAssistantPage = engine JS client-side

Le wizard 8 étapes calcule les scénarios **côté client** (JavaScript), pas via l'API `POST /api/purchase/compute`. Les résultats peuvent diverger du moteur serveur si les formules évoluent.

**Tag** : À RISQUE CRÉDIBILITÉ — Deux moteurs de calcul (client vs serveur)

---

## 9. Sources vérifiées

### Accise électricité

| Période | Taux T1 (repo) | Taux T1 (officiel) | Source officielle | Taux T2 (repo) | Taux T2 (officiel) | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| Jan 2025 | 0.02050 €/kWh | 20.50 €/MWh | [Légifrance — LdF 2024 prolongée](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000049059983) | — | — | ✅ Confirmé |
| Fév–Jul 2025 | 0.02623 | 26.23 €/MWh | [Légifrance — LdF 2025](https://www.legifrance.gouv.fr/codes/section_lc/LEGITEXT000044595989/LEGISCTA000044598377/) | 0.02569 | 25.69 €/MWh | ✅ Confirmé |
| Août 2025–Jan 2026 | 0.02998 | 29.98 €/MWh | [Ministère Écologie — Guide fiscalité 2025](https://www.ecologie.gouv.fr/sites/default/files/documents/Guide%202025%20sur%20la%20fiscalit%C3%A9%20des%20%C3%A9nergies.pdf) + facture ENGIE vérifiée | 0.02579 | 25.79 €/MWh | ✅ Confirmé primaire + secondaire |
| Fév 2026+ | 0.03085 | 30.85 €/MWh | [Légifrance — Arrêté 24/12/2025](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000053229989) | 0.02658 | 26.58 €/MWh | ✅ Confirmé primaire |

**Arbitrage** : Taux versionnés dans `catalog.py:625-679` vérifiés aux sources Légifrance + Guide fiscalité Ministère Écologie. Correspondance exacte. Le repo distingue T1 (ménages) et T2 (PME C4/C3) — **correct**.

**Niveau de certitude** : Confirmé primaire + secondaire

### TURPE 7

| Point | Source 1 | Source 2 | Verdict |
| --- | --- | --- | --- |
| Référence délibération | [Légifrance — CRE n°2025-78](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000051587195) (JO 14/05/2025) | [Enedis — Brochure TURPE 7](https://www.enedis.fr/media/4717/download) (01/08/2025) | **CRE n°2025-78**, en vigueur 01/08/2025 |
| Gestion C4 BT | 217.80 €/an (repo) | Brochure Enedis p.13 | ✅ Confirmé primaire |
| Comptage C4 BT | 283.27 €/an (repo) | Brochure Enedis p.13 | ✅ Confirmé primaire |
| TVA abo/gestion | 5.5% (repo) | Code fiscal | ✅ Confirmé |
| TVA énergie | 20% (repo) | Code fiscal | ✅ Confirmé |

**Niveau de certitude** : Confirmé primaire (CRE + Enedis)

### TICGN / accise gaz

| Période | Taux repo | Taux officiel | Source | Verdict |
| --- | --- | --- | --- | --- |
| 2025 (simplifié) | 0.01637 €/kWh | 17.16 €/MWh (plein tarif 2025) → **16.37 €/MWh** | [Légifrance — Arrêté 20/12/2024](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000050853048) | ⚠️ Le repo utilise 16.37 qui est le taux réduit (usage combustible hors chauffage collectif). Acceptable si appliqué au bon segment |
| Août 2025–Jan 2026 | — | 10.54 €/MWh | [Légifrance — Arrêté 24/07/2025](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000052009319) | NON TROUVÉ dans catalog.py — pas de versionnement gaz |
| Fév 2026+ | — | 10.73 €/MWh | [Légifrance — Arrêté 24/12/2025](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000053229989) | NON TROUVÉ dans catalog.py |

**Arbitrage** : L'accise gaz dans `billing_shadow_v2.py` est un **taux simplifié fixe** (0.01637 €/kWh), pas versionné comme l'accise élec. Le taux officiel 2025 (17.16 €/MWh) puis 10.54 puis 10.73 €/MWh n'est pas suivi. Simplification acceptable pour un POC élec-first, mais **fragile pour le gaz**.

**Niveau de certitude** : Probable mais versionnement gaz non fiabilisé

### Prix par défaut

| Point | Source 1 | Source 2 | Conflit ? |
| --- | --- | --- | --- |
| Default elec | `billing_service.py:43` → 0.15 €/kWh (env) | `config/default_prices.py:10` → 0.18 €/kWh | **OUI — 2 sources incohérentes** |
| Default gaz | `billing_service.py:44` → 0.08 €/kWh (env) | `config/default_prices.py:11` → 0.09 €/kWh | **OUI — 2 sources incohérentes** |

**Arbitrage** : `billing_service.py` (env var fallback) est **effectivement utilisé** par `get_reference_price()`. `config/default_prices.py` est utilisé par d'autres services (patrimoine_assumptions, usage_service). Le shadow billing utilise donc un prix **différent** des estimations patrimoine.

**Niveau de certitude** : Confirmé — incohérence avérée

---

## 10. Top P0 / P1 / P2

### P0 — Bloquant crédibilité

| # | Problème | Fichier:ligne | Impact |
| --- | --- | --- | --- |
| P0-1 | **Deux sources prix par défaut incohérentes** | `billing_service.py:43-44` (0.15/0.08) vs `config/default_prices.py:10-11` (0.18/0.09) | Shadow billing et estimations patrimoine divergent de 17-12.5% |

### P1 — Crédibilité marché

| # | Problème | Fichier:ligne | Impact |
| --- | --- | --- | --- |
| P1-1 | **Données marché = seed** — pas de feed EPEX Spot réel | `MarketPrice.source = "Seed PROMEOS"` | Scénarios achat avancés crédibles en structure mais avec données fictives |
| P1-2 | **Moteur grand public (3 factors fixes) toujours exposé via API** | `purchase_scenarios_service.py:40,69,100` | Un appel `GET /api/purchase/scenarios` retourne des résultats à écart constant |
| P1-3 | **PurchaseAssistant = engine JS client divergent du serveur** | `PurchaseAssistantPage.jsx` (engine JS) vs `purchase_service.py` (Python) | Calculs potentiellement différents |
| P1-4 | **Actions achat éphémères** | `purchase_actions_engine.py` | Centre d'actions vide sans sync explicite |
| P1-5 | **Accise gaz non versionnée** | `billing_shadow_v2.py` — taux fixe 0.01637 | Taux obsolète si factures gaz post-08/2025 (10.54→10.73 €/MWh) |

### P2 — Premium

| # | Problème | Impact |
| --- | --- | --- |
| P2-1 | Pas de feed prix marché temps réel (EPEX Day-Ahead) | Scénarios achat = photos statiques |
| P2-2 | Reconstitution gaz V2 non implémentée | ATRD/ATRT/TICGN = estimation simplifiée |
| P2-3 | Pas d'export CSV bulk des factures | Seuls les exports réconciliation et comparaison existent |
| P2-4 | Conformité ↔ Facture toujours cassé | Confirmé étape 1, non résolu |

---

## 11. Plan de correction priorisé

### Immédiat (1-2 jours)

| # | Action | Fichier | Effort |
| --- | --- | --- | --- |
| 1 | **Unifier prix par défaut** : supprimer les env vars fallback dans `billing_service.py` et utiliser `config/default_prices.py` comme source unique | `billing_service.py:43-44`, `config/default_prices.py` | XS |
| 2 | **Versionner accise gaz** dans catalog.py (ajouter TICGN_AOUT2025 = 10.54 et TICGN_FEV2026 = 10.73) | `billing_engine/catalog.py` | S |
| 3 | **Deprecation notice** sur `GET /api/purchase/scenarios` (moteur grand public) — orienter vers `POST /api/purchase/compute` | `routes/purchase.py`, docstring | XS |

### Court terme (1 semaine)

| # | Action | Fichier | Effort |
| --- | --- | --- | --- |
| 4 | Auto-sync actions achat à l'ouverture d'ActionsPage | `ActionsPage.jsx` | S |
| 5 | Aligner PurchaseAssistant sur l'API serveur (appeler `POST /purchase/compute` au lieu du JS engine) | `PurchaseAssistantPage.jsx` | M |
| 6 | Bandeau "données marché démo" si MarketPrice.source contient "Seed" | `MarketContextBanner.jsx` | S |

### Moyen terme (2-4 semaines)

| # | Action | Fichier | Effort |
| --- | --- | --- | --- |
| 7 | Intégrer feed EPEX Spot France Day-Ahead (API ou proxy RTE eCO2mix) | `connectors/`, `models/market_price.py` | L |
| 8 | Reconstitution gaz V2 (ATRD7 + ATRT + CTA gaz + TICGN) | `billing_engine/` | L |
| 9 | Lien conformité ↔ facture (bandeau risque + CTA croisés) | `BillIntelPage.jsx`, `ConformitePage.jsx` | S |

---

## 12. Definition of Done

| Critère | Statut |
| --- | --- |
| Reconstitution TURPE 7 vérifiée aux taux CRE n°2025-78 | FAIT — ✅ |
| Accise élec versionnée vérifiée (2023→2026) | FAIT — ✅ tous taux corrects |
| Accise gaz vérifiée | FAIT — ⚠️ taux fixe, non versionné post-08/2025 |
| 14 règles anomalie documentées avec seuils | FAIT |
| 20 règles audit V0 documentées | FAIT |
| Moteur achat avancé découvert et documenté | FAIT — 4 stratégies market-based |
| Profil RéFlex solaire audité | FAIT — 6 blocs horaires |
| Incohérence prix par défaut identifiée | FAIT — P0-1 |
| Liens facture→achat→actions tracés | FAIT — volume oui, anomalies non, actions éphémères |
| Sources vérifiées ×2 minimum | FAIT — Légifrance + CRE + Enedis + Ministère Écologie |

---

*Audit étape 3 réalisé le 2026-03-23. Prêt pour l'étape 4 : audit UX/UI sévère.*

Sources:
- [Légifrance — CRE n°2025-78 TURPE 7 HTA-BT](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000051587195)
- [Enedis — Grilles TURPE 7 au 01/08/2025](https://www.enedis.fr/media/4717/download)
- [Légifrance — Accise élec art. L312-18 à L312-87](https://www.legifrance.gouv.fr/codes/section_lc/LEGITEXT000044595989/LEGISCTA000044598377/)
- [Légifrance — Arrêté 24/12/2025 tarifs accises 2026](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000053229989)
- [Ministère Écologie — Guide 2025 fiscalité des énergies](https://www.ecologie.gouv.fr/sites/default/files/documents/Guide%202025%20sur%20la%20fiscalit%C3%A9%20des%20%C3%A9nergies.pdf)
- [Légifrance — Arrêté 20/12/2024 tarifs accises](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000050853048)
- [Légifrance — Arrêté 24/07/2025 actualisation tarifs](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000052009319)
