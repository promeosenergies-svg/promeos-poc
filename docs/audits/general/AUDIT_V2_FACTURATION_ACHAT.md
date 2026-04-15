# AUDIT V2 ULTRA-SÉVÈRE — BRIQUE PROMEOS "FACTURATION & ACHAT"

> **Date** : 11 mars 2026
> **Preuves** : Code source complet + facture réelle EDF BT >36 kVA (108 kVA, LU) + facture réelle gaz (PCE, T2, P012) + docs TURPE 7 + audit V1 (41/100)
> **Auditeur** : Chief Product Auditor énergie B2B France + Red Team réglementaire

---

## 1. RÉSUMÉ EXÉCUTIF

### Score global : 38/100 — NON CRÉDIBLE

Le score baisse de 41 à 38 par rapport à l'audit V1 car l'examen croisé code × factures réelles révèle des défauts plus graves que soupçonné :

1. **Bug bloquant** : `_resolve_segment(contract)` cherche `subscribed_power_kva` sur `EnergyContract` — ce champ **n'existe pas** sur ce modèle (il est sur `Meter`). Résultat : **le segment TURPE est TOUJOURS C5_BT**, même pour un contrat 108 kVA (C4 BT). Tout le shadow billing est structurellement faux pour tout site >36 kVA.
2. **Assiette CTA fausse** : le code calcule `CTA = 27.04% × turpe_gestion_mois × prorata`. La facture réelle montre : assiette CTA = 308,90 EUR = gestion (17,90) + comptage (23,28) + soutirage fixe (267,72). La composante soutirage fixe (267,72 EUR) est **totalement absente** du calcul PROMEOS. Écart : ~80 EUR/mois sur cette seule facture.
3. **TURPE C4 inexistant** : la facture réelle montre 5 composantes TURPE distinctes (gestion, comptage, soutirage fixe, soutirage HPE, soutirage HCE). PROMEOS a un seul taux plat × kWh. L'écart structurel dépasse 50%.
4. **Le gaz est une façade** : la facture gaz réelle montre PCE, profil P012, tarif T2, CAR, GRTgaz/GRDF. PROMEOS a un taux ATRD plat sans profil, sans PCS, sans distinction transport/distribution.
5. **L'achat est du bruit décoratif** : risk scores hardcodés, P10/P90 = ×0.85/×1.20, pas de courbe forward.

### 5 faiblesses majeures

1. **`_resolve_segment` retourne TOUJOURS C5_BT** — `subscribed_power_kva` absent de `EnergyContract`
2. **Assiette CTA = seulement gestion** — manque comptage + soutirage fixe (80%+ de l'assiette réelle pour C4)
3. **Pas de composantes TURPE réelles** — gestion/comptage/soutirage fixe/soutirage HPE/HCE absents, remplacés par un taux × kWh
4. **Un seul prix par contrat** — pas de prix par période tarifaire (HPE/HCE/HP/HC/Pointe)
5. **Pas de puissance souscrite sur le contrat** — impossible de calculer le soutirage fixe

### 3 forces réelles

1. **`compute_shadow_breakdown` existe** et a la bonne architecture (components[], gap, status, catalog_trace) — il faut remplacer le contenu, pas la structure
2. **Catalogue tarifaire versionné** avec `valid_from/valid_to` et source CRE — bonne fondation à enrichir
3. **14 règles d'anomalie + coverage engine + radar contrats** — fonctionnels, utiles, à conserver

### CHOIX STRATÉGIQUE : OPTION B — "BT >36 kVA standard crédible"

**Justification impitoyable :**

| Critère | Option A (C5) | Option B (BT >36 kVA) |
|---------|---------------|------------------------|
| **ICP** | Résidentiel / petit pro — hors cible | Tertiaire multi-sites — exactement l'ICP |
| **Facture réelle fournie** | Ne correspond PAS (la facture est 108 kVA) | Correspond EXACTEMENT |
| **Test prospect** | Un DAF testera avec ses factures (>36 kVA) | Passe le test |
| **Complexité TURPE** | Triviale (base ou HP/HC, pas de soutirage fixe) | 5 composantes mais finie et documentée |
| **Effort** | 2 semaines pour un truc inutile au prospect | 4 semaines pour un truc démontrable |
| **Crédibilité** | "Vous ne gérez que le résidentiel ?" | "Vous reconstituez ma facture composante par composante" |
| **Différenciation** | Aucune — tout le monde fait du C5 | Vraie — peu de SaaS reconstituent le C4 BT |

**Verdict : Option A est un piège.** Le C5 ≤36 kVA n'est PAS le segment de la cible B2B France. La facture réelle fournie est un BT >36 kVA. Si PROMEOS ne sait pas reconstituer CETTE facture, il ne passe pas la première démo. Un wedge C5 serait techniquement plus simple mais commercialement inutile.

**Option B est exécutable en 4 semaines** car :
- La structure TURPE 7 pour C4 BT est finie (5 composantes connues)
- Les taux sont publics (délibération CRE)
- Le modèle de données PROMEOS a la bonne architecture (components[], catalog)
- L'effort est concentré : corriger le moteur, pas reconstruire l'app

---

## 2. FAITS

### 2.1 Présents et prouvés (code + exécution)

**Modèle de données :**
- `EnergyContract` : site_id, energy_type, supplier_name, start_date, end_date, price_ref_eur_per_kwh, fixed_fee_eur_per_month, notice_period_days, auto_renew, offer_indexation, contract_status, reference_fournisseur, date_signature, conditions_particulieres
- `EnergyInvoice` : site_id, contract_id, invoice_number, period_start, period_end, issue_date, total_eur, energy_kwh, status
- `EnergyInvoiceLine` : invoice_id, line_type (ENERGY/NETWORK/TAX/OTHER), label, qty, unit, unit_price, amount_eur
- `DeliveryPoint` : code (14 chars), energy_type (ELEC/GAZ), site_id, status
- `ConceptAllocation` : invoice_line_id → concept_id (fourniture, acheminement, taxes...)
- N-N Contract ↔ DeliveryPoint via `contract_delivery_points`

**Shadow billing V2 :**
- Fonction `shadow_billing_v2()` : décomposition en 4 composantes (fourniture, réseau, taxes, abonnement) avec TVA per-composante
- Fonction `compute_shadow_breakdown()` : enrichit V2 avec CTA, segment dynamique, gaps par composante
- Catalog trace et diagnostics (assumptions, confidence, missing_fields)
- Rates depuis `tax_catalog.json` avec fallback YAML puis hardcodé

**14 règles d'anomalie :**
- R1 shadow_gap (>20%), R2 unit_price_high, R3 duplicate, R4 missing_period, R5 period_too_long, R6 negative_kwh, R7 zero_amount, R8 lines_sum_mismatch, R9 consumption_spike, R10 price_drift, R11 TTC_coherence, R12 contract_expiry, R13 TURPE_mismatch (via V2), R14 taxes_mismatch (via V2)

**Coverage + reconciliation :**
- Coverage mensuelle avec seuils 80%/60%
- Réconciliation mesuré vs facturé (seuil 10%)
- Radar de renouvellement contrat avec urgence (red/orange/yellow/green/gray)

**Catalogue tarifaire :**
- `tarifs_reglementaires.yaml` : TURPE 7 (3 segments), accises, CTA, TVA, prix référence
- `tax_catalog.json` : entrées versionnées avec valid_from/valid_to, source, fallback
- `tax_catalog_service.py` : lookup par date + audit trace

### 2.2 Absents (critiques pour ICP BT >36 kVA)

| Absent | Impact sur facture réelle 108 kVA |
|--------|-----------------------------------|
| **`subscribed_power_kva` sur EnergyContract** | Impossible de résoudre le segment TURPE |
| **Composante de comptage TURPE** | Manque 23,28 EUR/mois sur la facture réelle |
| **Composante de soutirage fixe TURPE** (puissance × taux) | Manque 267,72 EUR/mois sur la facture réelle |
| **Composantes de soutirage variable HPE/HCE** | TURPE variable résumé en 1 taux plat vs 2 taux réels |
| **Prix par période tarifaire sur le contrat** (HPE/HCE/HP/HC) | Un seul `price_ref_eur_per_kwh` = impossible de reconstituer la fourniture |
| **Option tarifaire sur DeliveryPoint** (Base/HP-HC/4 plages/5 plages) | Pas d'option → pas de ventilation |
| **Puissance souscrite par poste horosaisonnier** | Pas de vérification soutirage fixe vs souscrit |
| **Index de relève** (début/fin période) | Pas de vérification kWh facturés |
| **Type de facture** (acompte/solde/régularisation/avoir) | Tout traité comme facture normale |
| **Reprise / échu / échoir** | Pas de gestion des périodes de transition |
| **Coefficient de conversion gaz (PCS)** | m³ → kWh non traçable |
| **Profil gaz (T1/T2/T3/T4)** | ATRD = taux plat unique |
| **Campagne d'achat** (workflow multi-offres) | Pas de modèle |

### 2.3 Faux ou douteux (preuves code)

| Élément | Code | Facture réelle | Écart |
|---------|------|----------------|-------|
| **Segment TURPE** | `_resolve_segment(contract)` → toujours C5_BT car `subscribed_power_kva` absent de EnergyContract | BT >36 kVA = C4 BT (108 kVA) | **100% faux** pour tout site >36 kVA |
| **Assiette CTA** | `cta_base = turpe_gestion * (days/30)` = 18,48 × 1,0 = 18,48 EUR | Assiette CTA = 308,90 EUR (gestion + comptage + soutirage fixe) | **Sous-estimation ×16,7** |
| **Taux CTA** | 27,04% (catalog) | 21,93% (facture réelle) | Taux probablement pour une période antérieure sur la facture — mais le code ne gère pas le versioning par date |
| **TURPE réseau** | `kwh × 0.0453` (C5) ou `kwh × 0.0390` (C4, jamais atteint) | 5 composantes distinctes totalisant ~794 EUR | **Impossible à comparer** — structures incompatibles |
| **Prorata** | `days_in_period / 30.0` | Mois calendaire réel | Écart 0-10% (février = 28j/30 = 0.933, réel = 1.0) |
| **Confiance "high"** | Affiché si contrat + 2 types de lignes | Le calcul est structurellement faux même avec toutes les données | **Trompeur** |
| **"Shadow billing"** | Multiplication kWh × prix + taux plat TURPE | Vraie reconstitution = 10+ composantes par ligne | **Appellation trompeuse** |
| **P10/P90** | `total × 0.85` / `total × 1.20` | Aucun fondement statistique | **Décoration quantitative** |

### 2.4 Non démontré

- Que le shadow billing V2, même corrigé, produirait un résultat à ±5% de la facture réelle fournie
- Que les taux TURPE 7 dans le YAML correspondent exactement aux taux CRE en vigueur pour le C4 BT
- Que le coverage engine détecte correctement les régularisations vs les trous
- Que le moteur d'achat apporte plus de valeur qu'un courtier + Excel
- Que le frontend est utilisable par un non-expert pour comprendre sa facture

---

## 3. HYPOTHÈSES

### 3.1 Hypothèses implicites détectées

| # | Hypothèse | Où dans le code | Danger |
|---|-----------|-----------------|--------|
| H1 | Le contrat porte la puissance souscrite | `_resolve_segment(contract)` | **FATAL** — le champ n'existe pas sur EnergyContract |
| H2 | Un seul taux TURPE énergie par segment suffit | `shadow_billing_v2` ligne 150 | **CRITIQUE** — ignore gestion/comptage/soutirage fixe/HPE/HCE |
| H3 | L'assiette CTA = gestion seule | `compute_shadow_breakdown` ligne 456 | **CRITIQUE** — manque comptage + soutirage fixe = 94% de l'assiette réelle |
| H4 | Un seul prix de fourniture par contrat | `EnergyContract.price_ref_eur_per_kwh` | **ÉLEVÉ** — la facture réelle a 2+ prix (HPE/HCE) |
| H5 | Prorata = days/30 | `shadow_billing_v2` ligne 142 | **MOYEN** — erreur systématique |
| H6 | Le gaz = élec avec d'autres taux | `shadow_billing_v2` ligne 153-156 | **ÉLEVÉ** — PCS, T1-T4, transport/distribution ignorés |
| H7 | Les factures sont toujours de consommation | Pas de type acompte/solde/régul | **ÉLEVÉ** — faux positifs sur R1/R9/R11 |
| H8 | P10/P90 = plage de confiance | `purchase_service.py` | **ÉLEVÉ** — facteurs constants sans fondement |
| H9 | Risk score = indicateur fiable | Hardcodé 20/55/80/40 | **ÉLEVÉ** — ne dépend d'aucun paramètre marché/client |

### 3.2 Hypothèses dangereuses

- **H1 + H2 + H3 combinés** = le shadow billing est structurellement inutilisable pour tout site >36 kVA. C'est 100% de l'ICP.
- **H4** = la fourniture est sous/surestimée pour tout contrat multi-plages horaires.
- **H6** = toute la brique gaz est un affichage décoratif.

### 3.3 Acceptables en V1 (OPTION B)

- Pas de C1/C2/C3 HTA — hors cible PME/tertiaire
- Accise = taux unique (ok pour <250 GWh/an)
- Pas d'énergie réactive (ok pour tertiaire standard)
- Pas de mécanisme de capacité (ajout V2)
- Gaz = lecture simple sans reconstitution (explicité au client)
- Pas d'ingestion Enedis/GRDF automatique (import CSV/manuel)

### 3.4 À tester immédiatement

| Test | Effort | Quand |
|------|--------|-------|
| Reconstituer la facture réelle EDF 108 kVA avec le moteur corrigé → viser ±2% | 2 jours | Semaine 2 |
| Vérifier les taux TURPE 7 C4 BT (LU et MU) contre la délibération CRE officielle | 2 heures | Semaine 1 jour 1 |
| Vérifier le taux CTA en vigueur au 11/03/2026 vs 21,93% (facture) vs 27,04% (code) | 1 heure | Semaine 1 jour 1 |
| Tester le coverage engine avec des factures de régul → détecte-t-il des faux trous ? | 1 jour | Semaine 3 |

---

## 4. DÉCISIONS

### 4.1 Ce qu'on garde

- Architecture `compute_shadow_breakdown()` — components[], gap, status, catalog_trace → **remplacer le contenu, pas la structure**
- Catalogue tarifaire versionné (tax_catalog.json + YAML) → **enrichir avec C4 BT complet**
- 14 règles d'anomalie → **conserver et ajuster les seuils après correction du moteur**
- Coverage engine → **conserver tel quel**
- Radar contrats → **conserver, ajouter puissance souscrite**
- Import CSV/JSON + idempotence → **conserver**
- Frontend BillingPage / BillIntelPage → **conserver, adapter les composantes affichées**

### 4.2 Ce qu'on supprime

| À supprimer | Raison |
|-------------|--------|
| Label **"confiance: high"** | Trompeur — le calcul est structurellement faux |
| Label **"shadow billing"** pour la V1 simple | C'est `kWh × prix`, pas un shadow billing |
| **P10/P90** comme plage de confiance | Facteurs constants sans fondement statistique |
| **Risk scores hardcodés** (20/55/80/40) | Faux sentiment de rigueur quantitative |
| **Prétention d'expertise gaz** | Tant que pas d'ATRD segmenté + PCS + profil |
| **"Réseau (TURPE)"** comme composante unique | Doit être décomposé en composantes réelles |

### 4.3 Ce qu'on recode (OPTION B — BT >36 kVA)

| Quoi | Pourquoi | Effort |
|------|----------|--------|
| **Ajouter `subscribed_power_kva` + `tariff_option` sur EnergyContract** | Résoudre le segment TURPE et calculer le soutirage fixe | S (1j) |
| **Refaire `_resolve_segment()`** pour lire la puissance depuis Contract OU Meter | Corriger le bug fatal | XS (2h) |
| **Réécrire le moteur TURPE C4 BT** avec 5 composantes : gestion, comptage, soutirage fixe (kVA × taux), soutirage variable HPE, soutirage variable HCE | Reconstituer la vraie facture | M (5j) |
| **Corriger l'assiette CTA** = gestion + comptage + soutirage fixe (les 3 composantes fixes d'acheminement) | Conforme à la facture réelle | S (1j) |
| **Ajouter prix par plage horaire** sur le contrat (`price_hpe`, `price_hce` ou `price_schedule_json`) | Reconstituer la fourniture par période | S (2j) |
| **Enrichir `tax_catalog.json`** avec les taux TURPE C4 BT complets (gestion, comptage, soutirage fixe par kVA, soutirage HPE/kWh, soutirage HCE/kWh) | Alimenter le moteur | S (1j) |
| **Corriger le prorata** : `days / monthrange()[1]` au lieu de `days / 30` | Exactitude mathématique | XS (1h) |
| **Remplacer "confidence: high"** par 3 niveaux honnêtes : "reconstitution complète" (toutes composantes vérifiées), "estimation partielle" (composantes manquantes), "lecture seule" (pas de données) | Honnêteté UX | XS (2h) |
| **Ajouter `invoice_type`** sur EnergyInvoice : CONSOMMATION, ACOMPTE, REGULARISATION, AVOIR | Éviter les faux positifs | S (1j) |
| **Remplacer P10/P90** par `vol × prix × σ_historique × √(horizon/12)` | Minimum de rigueur | S (2j) |

### 4.4 Ce qu'on repousse en V2

| Quoi | Raison |
|------|--------|
| C3 HTA / C2 / C1 | Segments rares pour la cible, structure tarifaire beaucoup plus complexe (8 postes horosaisonniers) |
| Gaz shadow billing (ATRD T1-T4, PCS, stockage) | Complexité trop élevée pour V1, afficher en "lecture simple" |
| Énergie réactive (tg φ, pénalités) | Hors scope tertiaire standard |
| Mécanisme de capacité (certificats, obligation) | Ajout V2 (~2-4 EUR/MWh) |
| CEE (certificats d'économie d'énergie) | Ajout V2 |
| Ingestion PDF automatique (OCR) | Complexité/fiabilité trop risquée en V1 |
| API Enedis SGE / GRDF Datahub | Délai d'accès + complexité technique |
| Monte Carlo complet | V2 après données historiques suffisantes |
| Campagne d'achat (workflow multi-offres) | V2 |
| Avenant contractuel (modifications) | V2 — gérable manuellement en V1 |
| Reprise échu/échoir | V2 — cas rare en C4 BT standard |

---

## 5. TABLEAU DES ISSUES

| ID | Sev | Domaine | Description | Preuve | Impact Business | Impact Client | Impact Régl. | Impact Financier | Correctif | Effort | Priorité |
|----|-----|---------|-------------|--------|-----------------|---------------|--------------|------------------|-----------|--------|----------|
| **I01** | **S0** | backend/math | `_resolve_segment()` retourne TOUJOURS C5_BT car `subscribed_power_kva` absent de `EnergyContract` | `billing_shadow_v2.py:336` + `billing_models.py` — champ inexistant | Shadow billing faux pour 100% de l'ICP | Toute reconstitution >36 kVA est fausse | — | 100% des composantes TURPE erronées | Ajouter `subscribed_power_kva` sur EnergyContract + corriger `_resolve_segment` | S (1j) | **Now S1J1** |
| **I02** | **S0** | math/régl | Assiette CTA = turpe_gestion seule. Manque comptage + soutirage fixe | `billing_shadow_v2.py:456` vs facture réelle (308,90 EUR vs ~18 EUR) | CTA sous-estimée ×16,7 | Écart de ~80 EUR/mois sur facture 108 kVA | CRE/CGI non-conforme | ~960 EUR/an par site C4 | CTA = taux × (gestion + comptage + soutirage_fixe) | S (1j) | **Now S1J1** |
| **I03** | **S0** | math/régl | TURPE = 1 seul taux plat × kWh au lieu de 5 composantes | `shadow_billing_v2.py:150-151`, `tarifs_reglementaires.yaml` vs facture réelle (794 EUR = 5 composantes) | Shadow billing structurellement incomparable avec une vraie facture | Le client ne retrouve AUCUNE ligne de sa facture | Non-conforme TURPE 7 | >50% d'écart sur composante réseau | Réécrire moteur TURPE C4 BT avec 5 composantes | M (5j) | **Now S1-S2** |
| **I04** | **S0** | data/contrat | Un seul `price_ref_eur_per_kwh` par contrat — pas de prix HPE/HCE | `EnergyContract` model — champ unique | Fourniture impossible à reconstituer pour contrat multi-plages | Écart fourniture inexpliqué | — | 10-30% d'écart sur fourniture | Ajouter `price_hpe`, `price_hce` (ou JSON) sur EnergyContract | S (1j) | **Now S1J2** |
| **I05** | **S1** | UX | "Confiance: high" affiché sur un calcul structurellement faux | `billing_shadow_v2.py:281-286` — conditions insuffisantes | Faux sentiment de maîtrise | Le client fait confiance à un résultat erroné | Commercialement trompeur | — | Remplacer par "reconstitution complète" / "estimation partielle" / "lecture seule" | XS (2h) | **Now S1J1** |
| **I06** | **S1** | data | Pas de type de facture (conso/acompte/régul/avoir) | `EnergyInvoice` — pas de champ `invoice_type` | Régularisations traitées comme factures normales → anomalies fantômes | Faux positifs R1/R9/R11 | — | Bruit dans les insights, perte de crédibilité | Ajouter `invoice_type` enum sur EnergyInvoice | S (1j) | **Now S1** |
| **I07** | **S1** | math | Prorata = days/30 au lieu de calendaire | `billing_shadow_v2.py:142` | Erreur systématique sur tous les mois ≠ 30 jours | Février : -6,7%, Janvier : +3,3% | — | ~3% en moyenne sur abonnement | `days / calendar.monthrange(year, month)[1]` | XS (1h) | **Now S1J1** |
| **I08** | **S1** | achat | P10/P90 = facteurs constants ×0.85/×1.20 | `purchase_service.py` — hardcodé | Fausses plages de confiance | Décision d'achat sur données fictives | Commercialement trompeur | Potentiel >100k EUR | `vol × prix × σ × √(horizon/12)` | S (2j) | **Now S2** |
| **I09** | **S1** | achat | Risk score hardcodé (Fixe=20, Indexé=55, Spot=80, RéFlex=40) | `purchase_service.py` — constantes | Aucune sensibilité au marché ni au client | Risque identique quelles que soient les conditions | Trompeur | — | Paramétrer par volatilité × horizon × profil | S (2j) | **Next S3** |
| **I10** | **S1** | gaz | ATRD7 = taux unique plat 0.025 EUR/kWh | `tarifs_reglementaires.yaml` | Faux pour profils T2-T4 | >30% d'écart possible | Non-conforme ATRD7 | 15-35% composante distribution | Downgradé en "lecture simple" V1, vrai moteur V2 | M | **Next (V2)** |
| **I11** | **S1** | gaz | Pas de PCS / coefficient thermique | Aucun champ dans MeterReading gaz | m³→kWh non vérifiable | Consommation gaz non auditable | — | Variable | Downgradé "lecture simple" V1 | S | **Next (V2)** |
| **I12** | **S2** | régl | Pas de versioning CTA par date — taux 27,04% vs 21,93% (facture réelle) | `tax_catalog.json:108` vs facture réelle | Taux potentiellement obsolète ou pour mauvaise période | Résultat CTA faux | Réglementaire | Variable | Vérifier immédiatement le taux CRE en vigueur, ajouter historique | S (1j) | **Now S1J1** |
| **I13** | **S2** | contrat | Pas d'option tarifaire (Base/HP-HC/4 plages/5 plages) | DeliveryPoint ni EnergyContract ne portent l'option | Impossible de déterminer les plages horaires applicables | Ventilation kWh impossible | — | — | Ajouter `tariff_option` enum sur EnergyContract ou DeliveryPoint | XS (2h) | **Now S1** |
| **I14** | **S2** | backend | Pas de mécanisme de capacité (MEOC) | Aucun modèle | Composante facture ignorée | ~2-4 EUR/MWh manquants | — | 2-4% | V2 | M | **Later** |
| **I15** | **S2** | UX | "Shadow billing" = appellation trompeuse sur V1 simple | `billing_service.py:123` — `kWh × price_ref` | Promesse d'audit non tenue | Client déçu en vérifiant | — | Risque réputation | Renommer "Estimation rapide" pour V1 simple, "Reconstitution" pour V2 | XS | **Now S1** |
| **I16** | **S2** | achat | Pas de courbe forward (EEX Cal, PEG) | `purchase_service.py` — EPEX Spot 30j seul | Stratégie indexée sans référence marché crédible | Recommandation déconnectée | — | — | V2 — intégrer EEX Cal Y+1 | M | **Later** |
| **I17** | **S3** | régl | Pas de versioning automatique + alerte "taux expiré" | Catalogue statique, pas de recalcul batch | Shadow billing obsolète silencieusement | — | Réglementaire | Variable | Ajouter check `valid_to` + alerte | S | **Next S4** |
| **I18** | **S3** | audit | Pas de traçabilité formule complète (inputs → calcul → output) | `catalog_trace` trace le taux mais pas le calcul | Non auditable par un tiers | — | — | — | Ajouter `calculation_trace` avec toutes les étapes | M | **Next S4** |

---

## 6. V1 CIBLE CRÉDIBLE

### Wedge retenu : "BT >36 kVA — Reconstitution de facture électricité + Radar contrats"

### Périmètre exact

**Segments supportés :**
- C4 BT (>36 kVA, ≤250 kVA) — segment principal ICP
- C5 BT (≤36 kVA) — supporté par défaut (sous-ensemble de C4)
- Options tarifaires : Longue Utilisation (LU), Moyenne Utilisation (MU)
- Plages horaires : HPE (Heures Pleines Été), HCE (Heures Creuses Été), HPH (Heures Pleines Hiver), HCH (Heures Creuses Hiver) pour LU ; HP/HC pour MU

**Types de factures supportés :**
- Facture de consommation (standard)
- Avoir (flag `is_credit_note`)
- Régularisation (flag `invoice_type = REGULARISATION`)
- Acompte (affiché mais non reconstitué — marqué "lecture seule")

**Types de contrats supportés :**
- Prix fixe mono-tarif (un prix kWh unique)
- Prix fixe multi-plages (HPE/HCE ou HP/HC — prix distincts)
- Indexé (prix variable + structure acheminement fixe)
- Reconduction tacite avec préavis

**Données minimales requises pour reconstitution :**
- Puissance souscrite (kVA) — sur le contrat ou le PDL
- Option tarifaire (LU/MU/Base) — sur le contrat ou le PDL
- kWh par plage horaire (HPE/HCE au minimum) — sur les lignes de facture
- Prix par plage horaire — sur le contrat
- Période de facturation (start/end)

**Composantes reconstituées (moteur V1) :**

| # | Composante | Calcul | TVA |
|---|------------|--------|-----|
| 1 | Fourniture HPE | kWh_HPE × prix_HPE | 20% |
| 2 | Fourniture HCE | kWh_HCE × prix_HCE | 20% |
| 3 | TURPE — Gestion | taux_gestion × prorata_mois | 5,5% |
| 4 | TURPE — Comptage | taux_comptage × prorata_mois | 5,5% |
| 5 | TURPE — Soutirage fixe | puissance_kVA × taux_soutirage_fixe × prorata_mois | 5,5% |
| 6 | TURPE — Soutirage HPE | kWh_HPE × taux_soutirage_HPE | 20% |
| 7 | TURPE — Soutirage HCE | kWh_HCE × taux_soutirage_HCE | 20% |
| 8 | CTA | taux_CTA × (gestion + comptage + soutirage_fixe) × prorata | 5,5% |
| 9 | Accise (TIEE) | kWh_total × taux_accise | 20% |
| 10 | TVA réduite | 5,5% × (composantes 3+4+5+8) | — |
| 11 | TVA normale | 20% × (composantes 1+2+6+7+9) | — |

**Limites assumées et affichées au client (disclaimer obligatoire) :**
- "Reconstitution V1 — segments C4 BT (LU/MU) et C5 BT. Les segments HTA (C3/C2/C1) ne sont pas encore supportés."
- "L'énergie réactive et le mécanisme de capacité ne sont pas inclus dans cette version."
- "Le gaz est affiché en lecture simple (sans reconstitution composante par composante)."
- "Les factures d'acompte sont affichées mais non reconstituées."
- "Les taux réglementaires sont mis à jour manuellement — vérifiez la date de validité dans le détail."

**Gaz en V1 :**
- Affichage "lecture simple" : montant TTC, kWh, fournisseur, période, PCE
- Pas de reconstitution (ATRD, PCS, profil non modélisés)
- Label explicite : "Facture gaz — lecture seule (reconstitution disponible en V2)"
- Radar contrats gaz : fonctionnel (échéance, renouvellement)

**Achat en V1 (corrigé) :**
- 4 stratégies maintenues (Fixe, Indexé, Spot, RéFlex Solar)
- P10/P90 remplacés par modèle paramétrique (σ historique)
- Risk score paramétré (volatilité × horizon × profil)
- Label : "Simulation indicative — ne constitue pas un conseil d'achat"
- Pas de campagne d'achat (workflow manuel)

---

## 7. BACKLOG DE PREUVES

| # | Hypothèse à valider | Impact si faux | Confiance | Facilité | Preuve attendue | Délai |
|---|---------------------|----------------|-----------|----------|-----------------|-------|
| P1 | Le moteur C4 BT corrigé reconstitue la facture réelle 108 kVA à ±2% par composante | BLOQUANT | FAIBLE | MOYEN | Import facture réelle → reconstitution → comparaison composante par composante | S2J5 |
| P2 | Les taux TURPE 7 C4 BT (LU) dans le catalogue correspondent à la délibération CRE | BLOQUANT | MOYEN | FACILE | Comparer tax_catalog enrichi vs PDF délibération CRE TURPE 7 | S1J1 |
| P3 | Le taux CTA en vigueur au 11/03/2026 est bien 27,04% (et pas 21,93% comme sur la facture) | ÉLEVÉ | FAIBLE | FACILE | Consulter arrêté CTA en vigueur, déterminer le taux par date | S1J1 |
| P4 | L'assiette CTA corrigée (gestion + comptage + soutirage fixe) donne un résultat à ±5 EUR de la facture réelle | ÉLEVÉ | MOYEN | FACILE | Recalculer manuellement sur facture réelle | S1J2 |
| P5 | Le prorata calendaire donne un résultat différent de >2 EUR vs days/30 | MOYEN | ÉLEVÉ | FACILE | Tester sur 3 factures : février, mars, avril | S1J1 |
| P6 | Les régularisations créent des faux positifs R1/R9 avec le moteur actuel | ÉLEVÉ | ÉLEVÉ | FACILE | Importer une facture de régul et observer les anomalies | S3J1 |
| P7 | Le P10/P90 paramétrique (σ historique) donne des plages plus réalistes que ×0.85/×1.20 | MOYEN | MOYEN | MOYEN | Comparer les 2 méthodes sur 12 mois historiques EPEX | S3 |
| P8 | Le frontend est utilisable par un non-expert pour comprendre sa facture | ÉLEVÉ | FAIBLE | MOYEN | Test utilisateur (5 personnes) sur le breakdown corrigé | S4 |

---

## 8. OBJECTION-KILLER

| # | Objection | Réponse | Preuve manquante |
|---|-----------|---------|------------------|
| 1 | *"Votre outil ne reconstitue pas ma facture — je ne retrouve pas mes composantes TURPE"* | V1 corrigée reconstitue les 5 composantes TURPE C4 BT (gestion, comptage, soutirage fixe, HPE, HCE) composante par composante. Testée sur une vraie facture EDF 108 kVA. | Benchmark sur 10 factures C4 BT réelles avec écart <2% par composante |
| 2 | *"La CTA est fausse dans votre breakdown"* | Corrigé : assiette = gestion + comptage + soutirage fixe, conforme à la structure CRE. Taux versionné par date. | Comparaison CTA PROMEOS vs CTA facture sur 10 factures |
| 3 | *"Vous ne gérez que le petit tarif C5"* | Non — V1 gère le C4 BT (>36 kVA ≤250 kVA), qui couvre >80% du tertiaire multi-sites. Le C5 est un sous-ensemble (plus simple). | Stats segment : % de l'ICP couvert par C4+C5 |
| 4 | *"Et pour mes sites en HTA ?"* | Hors scope V1. Les sites HTA (C3/C2/C1) ont une structure tarifaire plus complexe (8 postes horosaisonniers). Ils sont affichés en "lecture seule" en attendant V2. | Roadmap V2 avec échéance C3 HTA |
| 5 | *"Vos simulations d'achat ne valent pas un courtier"* | D'accord. PROMEOS n'est pas un courtier — c'est un cockpit qui vous donne la transparence. Le simulateur aide à structurer la discussion avec votre courtier, pas à le remplacer. | Témoignage d'un DAF : "PROMEOS m'a permis de challenger mon courtier" |
| 6 | *"Votre brique gaz est vide"* | En V1, le gaz est en "lecture simple" — on affiche vos factures, contrats, échéances. La reconstitution composante par composante (ATRD T1-T4, PCS) arrive en V2. C'est assumé et affiché. | Roadmap V2 gaz avec échéance |
| 7 | *"Comment je sais si vos taux sont à jour ?"* | Chaque composante affiche le taux utilisé, sa source (CRE/arrêté), sa date de validité. Si un taux est expiré, un avertissement apparaît. | Alerte "taux expiré" fonctionnelle dans le UI |
| 8 | *"Excel fait la même chose"* | Excel ne fait pas : détection automatique d'anomalies (14 règles), radar de renouvellement contrat, réconciliation mesuré/facturé, historique multi-sites, traçabilité. Et Excel ne scale pas à 50 sites. | Démo comparative : 5 factures × 10 sites dans PROMEOS vs Excel |
| 9 | *"Je veux voir le détail du calcul, pas juste le résultat"* | Chaque composante affiche : formule (kWh × taux), inputs, source du taux, date de validité, écart vs facture. Tout est traçable et exportable. | Capture d'écran du breakdown avec catalog_trace |
| 10 | *"Vos régularisations créent des anomalies fantômes"* | V1 distingue les types de facture (consommation, régul, acompte, avoir). Les réguls sont identifiées et traitées séparément pour éviter les faux positifs. | 0 faux positif sur 10 factures de régul importées |

---

## 9. PLAN DE REMÉDIATION 30 JOURS

### SEMAINE 1 (12-18 mars) — "Fondations C4 BT"

| Jour | Livrable | Owner | Vérifiable |
|------|----------|-------|------------|
| J1 | Vérifier taux CTA (21,93% vs 27,04%) contre arrêté officiel. Vérifier taux TURPE 7 C4 BT (LU/MU) contre délibération CRE. | Produit | Document de vérification signé |
| J1 | Ajouter `subscribed_power_kva` + `tariff_option` sur `EnergyContract`. Migration DB. | Backend | Test : `contract.subscribed_power_kva = 108` persiste |
| J1 | Corriger `_resolve_segment()` : lire puissance depuis Contract > Meter > None. | Backend | Test : contract 108 kVA → "C4_BT" |
| J1 | Corriger prorata : `monthrange()` au lieu de `/30`. | Backend | Test : février → prorata 1.0 sur mois complet |
| J1 | Remplacer "confidence: high" par "estimation indicative" / "reconstitution complète" / "lecture seule" | Backend+Front | Test : UI affiche le bon label |
| J2 | Enrichir `tax_catalog.json` avec taux TURPE 7 C4 BT complets : TURPE_GESTION_C4, TURPE_COMPTAGE_C4, TURPE_SOUTIRAGE_FIXE_C4_LU (EUR/kVA/an), TURPE_SOUTIRAGE_HPE_C4_LU (EUR/kWh), TURPE_SOUTIRAGE_HCE_C4_LU (EUR/kWh) | Backend | Test : `get_rate("TURPE_SOUTIRAGE_FIXE_C4_LU")` retourne le bon taux |
| J3 | Ajouter `price_hpe`, `price_hce` (+ optionnel `price_hph`, `price_hch`) sur EnergyContract. | Backend | Test : contrat multi-plages persiste |
| J4-J5 | Réécrire `shadow_billing_v2_c4()` avec les 11 composantes (cf. section 6). | Backend | Test unitaire : inputs connus → outputs attendus à ±0.01 EUR |

**Livrable S1** : Moteur C4 BT fonctionnel en backend avec taux vérifiés. Tests unitaires green.

### SEMAINE 2 (19-25 mars) — "Benchmark facture réelle"

| Jour | Livrable | Owner | Vérifiable |
|------|----------|-------|------------|
| J1-J2 | Importer la facture réelle EDF 108 kVA. Recréer le contrat avec les bonnes données (puissance, option, prix HPE/HCE). Exécuter le moteur. Comparer composante par composante. | Backend+Produit | Document : écart par composante, objectif ±2% |
| J2 | Corriger l'assiette CTA : gestion + comptage + soutirage fixe. Comparer avec les 308,90 EUR de la facture réelle. | Backend | Test : CTA PROMEOS = CTA facture ±5 EUR |
| J3 | Adapter `compute_shadow_breakdown()` pour afficher les 5+ composantes TURPE (pas 1 seule "réseau"). | Backend | API retourne components[] avec gestion, comptage, soutirage_fixe, soutirage_HPE, soutirage_HCE |
| J4-J5 | Adapter le frontend `ShadowBreakdownCard.jsx` pour afficher les nouvelles composantes, gaps, et statuts. | Frontend | Capture d'écran du breakdown C4 BT complet |

**Livrable S2** : Facture réelle 108 kVA reconstituée à ±2%. Frontend affiche le breakdown C4 complet.

### SEMAINE 3 (26 mars - 1 avril) — "Robustesse + Achat"

| Jour | Livrable | Owner | Vérifiable |
|------|----------|-------|------------|
| J1 | Ajouter `invoice_type` (CONSOMMATION/ACOMPTE/REGULARISATION/AVOIR) sur EnergyInvoice. Ajuster R1/R9/R11 pour ignorer les réguls/acomptes. | Backend | Test : import régul → pas de faux positif R1 |
| J2 | Ajouter C5 BT au moteur (HP/HC au minimum). Vérifier cohérence C5 vs ancien moteur. | Backend | Test : facture C5 HP/HC → reconstitution ±5% |
| J3 | Remplacer P10/P90 par modèle paramétrique (σ EPEX × √horizon). | Backend | Test : P10/P90 changent avec la volatilité du marché |
| J3 | Paramétrer risk score par volatilité × horizon × profil au lieu de constantes. | Backend | Test : même stratégie, 2 horizons → 2 risk scores différents |
| J4 | Downgradé gaz : afficher "lecture simple" avec label explicite. Désactiver shadow billing gaz. | Backend+Front | Test : facture gaz affiche "Lecture seule — reconstitution V2" |
| J5 | Tester sur 3 factures C4 BT réelles supplémentaires (si disponibles) ou seed réalistes. | Produit | Document : écarts par composante sur 3 factures |

**Livrable S3** : Moteur robuste (régul, C5, achat corrigé). Gaz honnêtement downgradé.

### SEMAINE 4 (2-8 avril) — "Démo-ready + disclaimers"

| Jour | Livrable | Owner | Vérifiable |
|------|----------|-------|------------|
| J1 | Ajouter disclaimers UI : limites V1 affichées dans le breakdown (segments supportés, composantes exclues). | Frontend | Capture d'écran disclaimers |
| J2 | Ajouter alerte "taux expiré" si `valid_to` < today sur une composante utilisée. | Backend+Front | Test : taux expiré → bandeau orange dans le breakdown |
| J3 | Seed HELIOS corrigé : contrats 108 kVA avec prix HPE/HCE, option LU, puissance souscrite. Factures avec bonnes composantes. | Backend | Test : seed → breakdown C4 BT cohérent |
| J4 | Script de démo 15 min : import facture → breakdown → anomalies → radar → achat. | Produit | Script validé par les 2 fondateurs |
| J5 | Audit final : relancer le score. Objectif : **65+/100** (base prometteuse). | Audit | Score documenté |

**Livrable S4** : Démo-ready avec disclaimers honnêtes. Score ≥65/100.

---

## 10. TOP 5 ACTIONS

| # | Action | Effort | Owner | Deadline |
|---|--------|--------|-------|----------|
| **1** | **Corriger le bug fatal** : ajouter `subscribed_power_kva` + `tariff_option` sur EnergyContract, corriger `_resolve_segment()`, corriger prorata, remplacer label "confidence: high" | **S** (1 jour) | Backend | **12 mars** (S1J1) |
| **2** | **Enrichir le catalogue tarifaire** avec les taux TURPE 7 C4 BT complets (gestion, comptage, soutirage fixe/kVA, soutirage HPE/kWh, soutirage HCE/kWh) — vérifiés contre la délibération CRE officielle + vérifier le taux CTA en vigueur | **S** (1 jour) | Backend + Produit | **13 mars** (S1J2) |
| **3** | **Réécrire le moteur shadow billing C4 BT** avec 11 composantes (cf. section 6) + prix par plage horaire sur le contrat | **M** (5 jours) | Backend | **18 mars** (fin S1) |
| **4** | **Benchmark facture réelle** : importer la facture EDF 108 kVA, reconstituer, comparer composante par composante, objectif ±2% | **S** (2 jours) | Backend + Produit | **21 mars** (S2J3) |
| **5** | **Corriger l'achat** : remplacer P10/P90 hardcodés par modèle paramétrique + risk score paramétré + downgradé gaz en "lecture simple" avec label honnête | **S** (3 jours) | Backend + Front | **28 mars** (fin S3) |

---

## GRILLE D'ÉVALUATION (V2)

| # | Dimension | Note V1 | Note V2 | Justification V2 |
|---|-----------|---------|---------|-------------------|
| 1 | Exactitude tarifaire électricité | 3/10 | **2/10** | Bug `_resolve_segment` = toujours C5. Pire que pensé : 100% de l'ICP en erreur |
| 2 | Exactitude tarifaire gaz | 2/10 | **2/10** | Inchangé — toujours un taux plat sans profil |
| 3 | Robustesse shadow billing / réconciliation | 3/10 | **2/10** | Assiette CTA ×16,7 en erreur. Le "shadow billing" est une appellation trompeuse |
| 4 | Qualité data model | 7/10 | **6/10** | `subscribed_power_kva` manquant sur Contract = défaut structurel du modèle |
| 5 | Gestion contrats et campagnes d'achat | 4/10 | **4/10** | Inchangé — un seul prix/contrat, pas de plages horaires |
| 6 | Explicabilité client | 4/10 | **3/10** | "Confidence: high" sur calcul faux = pire que pas de confidence |
| 7 | Maintenabilité réglementaire | 5/10 | **5/10** | Catalogue OK mais taux CTA potentiellement obsolète et pas d'alerte |
| 8 | Scalabilité multi-sites | 6/10 | **6/10** | Inchangé |
| 9 | Différenciation marché | 3/10 | **3/10** | Toujours pas mieux qu'Excel + courtier |
| 10 | Exécutabilité V1 à 2 fondateurs | 4/10 | **5/10** | Option B est réaliste en 4 semaines avec le plan ci-dessus |

### Score global V2 : 38/100

### Verdict : NON CRÉDIBLE (< 50)

### Score cible après remédiation 30 jours : 65-70/100 (base prometteuse)

**Le chemin est clair** : 4 semaines de travail concentré sur le moteur C4 BT transforment cette brique d'un squelette trompeur en un outil réellement différenciant pour le tertiaire B2B France. Le plan est exécutable à 2 fondateurs si et seulement si le scope est tenu (pas de gaz, pas de HTA, pas de Monte Carlo).

---

*Fin de l'audit V2 — 11 mars 2026*
