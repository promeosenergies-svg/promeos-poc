# AUDIT ULTRA-SÉVÈRE — BRIQUE PROMEOS "FACTURATION & ACHAT"

> **Audité le 11 mars 2026** — Code source analysé exhaustivement (24 modèles, 15+ services, toutes routes, tout frontend, seeds, tests, configuration tarifaire)
>
> **Auditeur** : Chief Product Auditor énergie B2B France + Expert facturation/achat électricité & gaz + Red Team réglementaire

---

## 1. RÉSUMÉ EXÉCUTIF

**Score global : 41/100 — NON CRÉDIBLE EN L'ÉTAT**

PROMEOS dispose d'une architecture propre et d'une mécanique de seed/démo impressionnante, mais la brique "Facturation & Achat" est un **squelette fonctionnel habillé en expert**. Le shadow billing est une multiplication simple (kWh × prix), le TURPE est réduit à un seul coefficient par segment au lieu d'une décomposition multi-composantes, la CTA est mal calculée, le gaz est traité en copier-coller de l'élec avec des taux plaqués, et le moteur d'achat produit des scénarios à scores de risque hardcodés sans aucune modélisation stochastique réelle.

**Face à un directeur achats énergie ou un DAF, cette brique ne tient pas 5 minutes d'examen technique.**

### 5 faiblesses majeures

1. **Shadow billing V2 = approximation grossière** — Pas de décomposition TURPE réelle (soutirage, comptage, dépassement, réactif absents), CTA sur mauvaise assiette
2. **Zéro moteur de reconstitution de facture** — Impossible de recalculer une facture ligne à ligne depuis les données réseau
3. **Modèle de contrat trop simpliste** — Pas d'avenant, pas de clause pass-through, pas de période tarifaire, pas de profil de courbe
4. **Achat = 4 stratégies statiques à risque hardcodé** — P10/P90 sont des multiplicateurs fixes (×0.85/×1.20), pas de Monte Carlo, pas de courbe forward
5. **Gaz = copier-coller** — ATRD7 en un seul taux plat, pas de T1-T4, pas de conversion PCS, pas de stockage

### 3 forces réelles

1. **Architecture data model solide** — Hiérarchie Org→Entité→Portefeuille→Site→PDL/PCE bien structurée, soft delete, audit trail
2. **14 règles d'anomalies** — Couverture correcte des cas basiques (doublons, trous, spikes, écarts)
3. **Seed/démo industrialisé** — 5 sites, 36 mois de factures, contrats réalistes, anomalies injectées = démo convaincante en surface

---

## 2. FAITS

### 2.1 Ce qui est présent et fonctionnel

- Modèle `EnergyContract` avec champs V96 (indexation, statut, alerte renouvellement, référence fournisseur, date signature, conditions particulières)
- Modèle `EnergyInvoice` + `EnergyInvoiceLine` avec 4 types (ENERGY, NETWORK, TAX, OTHER)
- `DeliveryPoint` lié à Site et Contract (N-N via `contract_delivery_points`)
- Shadow billing V1 : `energy_kwh × price_ref` avec cascade de résolution (contrat → marché EPEX 30j → profil tarifaire site → défaut hardcodé)
- Shadow billing V2 : décomposition en 5 composantes (fourniture, réseau, taxes, abonnement, TVA) avec `catalog_trace` et diagnostics
- 14 règles d'anomalie avec seuils définis (R1-R14)
- Couverture mensuelle (coverage engine) avec détection de trous, partials, avoirs exclus
- Réconciliation mesuré (MeterReading) vs facturé (EnergyInvoice) avec seuil 10%
- Catalogue tarifaire versionné (`tax_catalog.json` avec `valid_from/valid_to` + `tarifs_reglementaires.yaml`)
- 4 stratégies d'achat (Fixe, Indexé, Spot, RéFlex Solar avec blocs horaires pondérés)
- Radar de renouvellement contrat avec scoring d'urgence (red/orange/yellow/green/gray)
- Consommation unifiée (metered vs billed vs reconciled) avec sélection automatique par couverture
- Frontend complet : BillingPage (timeline), BillIntelPage (anomalies), PurchasePage (simulation), PurchaseAssistantPage (wizard 8 étapes)
- Explainability : top 3 contributeurs à l'écart TTC
- Normalisation facture : vue Pydantic InvoiceNormalized (HT, fourniture, réseau séparés)
- Import CSV/JSON avec batch tracking et idempotence (invoice_number + site_id + period)
- Règles de paiement 3 niveaux (portefeuille, site, contrat) avec entité payeuse distincte
- Contexte marché (EPEX Spot FR) avec trend vs 12 mois et recommandation d'action

### 2.2 Ce qui est absent

| Catégorie | Élément absent |
|-----------|----------------|
| **Moteur facture** | Reconstitution de facture ligne à ligne depuis données réseau/index |
| **TURPE** | Décomposition réelle (soutirage pointe/HPH/HCH/HPB/HCB, comptage, dépassement) |
| **Puissance** | Suivi Pmax souscrite vs atteinte, détection de dépassement |
| **Réactif** | Énergie réactive (cos φ, pénalités tg φ > 0.4) |
| **Capacité** | Mécanisme de capacité (obligation, certificats, ~2-4 EUR/MWh) |
| **CEE** | Certificats d'économie d'énergie (part refacturable) |
| **Contrat** | Modèle d'avenant (modifications contractuelles sans nouveau contrat) |
| **Contrat** | Périodes tarifaires (pointe, HPH, HCH, HPB, HCB) |
| **Contrat** | Clauses pass-through modélisées |
| **Contrat** | Coefficient de profil/forme lié au contrat |
| **Billing** | Gestion HP/HC dans le shadow billing (tout est en taux plat par segment) |
| **Billing** | Régularisation (type de facture dédié, logique estimé→réel→régul) |
| **Billing** | Avoir (pas de modèle dédié, seule la couverture exclut total_eur ≤ 0) |
| **Billing** | Prorata temporis rigoureux (le prorata = days/30 au lieu de calcul calendaire exact) |
| **Gaz** | Conversion PCS (coefficient thermique, m³→kWh) |
| **Gaz** | ATRD7 segmenté (T1/T2/T3/T4 selon profil de consommation) |
| **Gaz** | ATRT segmenté (distinction réseau transport) |
| **Gaz** | Stockage (coût de stockage, terme fixe/variable) |
| **Data** | Courbe de charge dans le moteur de facture (existe en MeterReading mais pas exploitée pour billing) |
| **Data** | Index de relève (début/fin de période) |
| **Data** | Données réseau distinctes (flux Enedis C5/C4) |
| **Achat** | Forward curve / courbe à terme |
| **Achat** | Monte Carlo réel (P10/P90 = facteurs constants ×0.85/×1.20) |
| **Achat** | Campagne d'achat (workflow multi-offres, négociation, validation) |
| **Achat** | Comparateur d'offres structuré (wizard existe mais moteur d'évaluation absent) |
| **Achat** | Gouvernance décisionnelle (validation multi-niveaux, traçabilité) |
| **Ingestion** | Connecteur API Enedis SGE / GRDF Datahub |
| **Ingestion** | Parser PDF facture automatique (stub existe, pas fonctionnel) |

### 2.3 Ce qui est faux ou douteux

| Élément | Problème | Impact |
|---------|----------|--------|
| **CTA** | Appliquée comme % brut (27.04% / 20.80%) mais **l'assiette est fausse**. La CTA s'applique sur la part fixe de l'acheminement (abonnement TURPE), pas sur le total ou la consommation. Le code ne distingue pas l'assiette. | Écart systématique 2-8% sur la facture |
| **TURPE "énergie"** | Un seul taux par segment (C5=0.0453, C4=0.039, C3=0.026). En réalité le TURPE a une composante de soutirage variable selon les heures (HPH/HCH/HPB/HCB pour C4+) et une composante fixe de gestion + comptage. Le taux unique est une approximation grossière. | Écart 10-25% sur composante réseau pour C4+ |
| **Résolution segment TURPE** | Basée uniquement sur kVA souscrit (≤36=C5, ≤250=C4, >250=C3). Ignore C1 et C2. | Acceptable V1 mais C3/C4 sous-modélisés |
| **Accise élec** | Taux unique 0.02250 EUR/kWh. PME >250 GWh/an ont des taux réduits, électro-intensifs aussi. | Acceptable pour cible PME <250 GWh |
| **ATRD gaz** | 0.025 EUR/kWh plat. Le vrai ATRD7 a des termes fixes et variables dépendant du profil T1-T4. | Écart >30% possible sur profil T4 |
| **Prorata** | `days_in_period / 30.0` au lieu de `days / jours_réels_du_mois`. | Erreur systématique 0-10% sur abonnement |
| **Confiance "high"** | Le frontend affiche "confiance: high" sur le shadow billing alors que le calcul utilise des taux uniques et une CTA absente. | Faux sentiment de fiabilité |
| **P10/P90** | `p10 = total × 0.85`, `p90 = total × 1.20` — facteurs constants sans aucun lien avec la volatilité réelle du marché. | Plages de confiance fictives |

### 2.4 Ce qui est non démontré

- Que le shadow billing V2 produit des résultats à ±5% d'une vraie facture sur des données réelles
- Que les taux TURPE/accises sont mis à jour lors des évolutions réglementaires (pas de mécanisme de migration/alerte)
- Que le moteur d'achat produit des recommandations utiles vs un courtier
- Que la réconciliation mesuré/facturé détecte les vrais écarts réseau vs fournisseur
- Que le coverage engine fonctionne correctement sur un historique réel (testé uniquement sur seed)

---

## 3. HYPOTHÈSES

### 3.1 Hypothèses implicites détectées

| # | Hypothèse implicite | Niveau de danger |
|---|---------------------|------------------|
| H1 | Un seul taux TURPE énergie par segment suffit | **ÉLEVÉ** — écart 10-25% sur C4/C3 avec profil saisonnier |
| H2 | La CTA = % du total | **CRITIQUE** — erreur d'assiette, écart systématique |
| H3 | Tous les clients sont au même taux d'accise | **MOYEN** — ok pour PME <250 GWh |
| H4 | Le gaz se facture comme l'élec avec des taux différents | **ÉLEVÉ** — ignore PCS, stockage, profils T1-T4 |
| H5 | P10/P90 = total × facteur fixe | **ÉLEVÉ** — aucune valeur prédictive réelle |
| H6 | Un contrat = un site | **MOYEN** — le modèle a un FK site_id direct, mais N-N via DeliveryPoint |
| H7 | Les factures ont toujours des kWh | **MOYEN** — factures d'abonnement seul, de régul, d'avoir n'en ont pas |
| H8 | Le prix de référence marché = moyenne spot 30j | **ÉLEVÉ** — ne reflète pas le prix forward contractuel |
| H9 | La couverture mensuelle = proxy de complétude | **MOYEN** — ne détecte pas les factures d'acompte vs solde |
| H10 | Le mesuré (MeterReading) est fiable | **MOYEN** — pas de flag `is_estimated` sur les index |

### 3.2 Hypothèses dangereuses

- **H1 + H2 combinées** signifient que le shadow billing est structurellement faux pour tout client C4+
- **H4** signifie que toute la brique gaz est une façade non défendable
- **H5** signifie que les recommandations d'achat sont du bruit décoratif présenté comme de l'analyse

### 3.3 Hypothèses acceptables en V1

- Accise unique (H3) — ok pour cible PME/tertiaire < 250 GWh
- Un contrat par site (H6) — ok si explicité comme limitation connue
- Pas de C1/C2 — ok, segments rares pour la cible tertiaire/PME
- Couverture mensuelle comme proxy (H9) — ok en première approche

### 3.4 Hypothèses à tester immédiatement

| Hypothèse | Test | Effort | Délai |
|-----------|------|--------|-------|
| H1 | Prendre 3 vraies factures C5 HP/HC et vérifier shadow billing à ±5% | 1 jour | Immédiat |
| H2 | Recalculer CTA sur part fixe acheminement et comparer avec résultat actuel | 2 heures | Immédiat |
| H4 | Prendre 1 vraie facture gaz T3 et tenter une reconstitution | 1 jour | Semaine 1 |
| H5 | Comparer P10/P90 hardcodés vs simulation historique 2 ans EPEX | 2 jours | Semaine 2 |

---

## 4. DÉCISIONS

### 4.1 Ce qu'il faut garder

- Architecture data model (Org→Entité→Portefeuille→Site→DeliveryPoint)
- Les 14 règles d'anomalie (enrichir, pas remplacer)
- Le coverage engine (utile, bien conçu, gestion avoirs correcte)
- Le radar de renouvellement contrat (valeur immédiate, urgence bien modélisée)
- La structure catalogue versionné (`tax_catalog.json` + `tarifs_reglementaires.yaml`)
- L'explainability (top 3 contributeurs — à fiabiliser)
- L'import CSV/JSON avec idempotence
- Le contexte marché EPEX (base utile, à enrichir)

### 4.2 Ce qu'il faut supprimer

- Le label "shadow billing" sur la V1 simple — c'est une multiplication, pas un shadow billing
- L'affichage de "confiance: high" quand le calcul utilise des taux uniques et une CTA absente
- Les P10/P90 comme "plage de confiance" — c'est trompeur, afficher "fourchette indicative" au minimum
- La prétention d'expertise gaz tant que le moteur n'est pas structuré (ATRD, PCS)

### 4.3 Ce qu'il faut recoder

| Élément | Correction | Effort |
|---------|------------|--------|
| **CTA** | Assiette = part fixe acheminement (turpe_gestion × prorata_mois), pas % du total | S (2j) |
| **Shadow billing V2** | Ajouter composante comptage, distinguer HP/HC pour C5, corriger prorata | M (5j) |
| **Prorata** | `days / calendar.monthrange(year, month)[1]` au lieu de `days / 30` | XS (0.5j) |
| **P10/P90** | `volume × prix × σ_historique × √(horizon/12)` au minimum | S (3j) |
| **Label confiance** | "Estimation indicative" au lieu de "confiance: high" | XS (0.5j) |
| **Risk score achat** | Paramétrer par volatilité + horizon + profil au lieu de constantes | S (2j) |

### 4.4 Ce qu'il faut repousser en V2

- TURPE multi-composantes complet pour C4/C3 (HPH/HCH/HPB/HCB + dépassement)
- Énergie réactive et pénalités tg φ
- Mécanisme de capacité
- Gaz ATRD7 segmenté T1-T4 + conversion PCS
- Monte Carlo complet avec simulation stochastique
- PPA / structuré / click pricing dans l'achat
- Ingestion PDF automatique avec OCR
- Connecteur API Enedis SGE / GRDF Datahub
- Campagne d'achat avec workflow multi-offres
- Avenant contractuel avec historique de modifications

---

## 5. TABLEAU DES ISSUES

| ID | Sev | Domaine | Description | Preuve / Symptôme | Risque Business | Risque Client | Risque Régl. | Impact Financier | Correctif recommandé | Effort | Priorité |
|----|-----|---------|-------------|-------------------|-----------------|---------------|--------------|------------------|----------------------|--------|----------|
| I01 | **S0** | math | CTA sur mauvaise assiette | `billing_shadow_v2.py` : CTA jamais calculée dans la décomposition V2 — absente du modèle | Résultat faux affiché comme "audité" | Perte de confiance immédiate si client vérifie | Non-conforme | 2-8% de la facture | Calculer CTA = taux × part_fixe_acheminement (turpe_gestion × prorata) | S | **Now** |
| I02 | **S0** | math | TURPE = taux unique plat par segment | `tarifs_reglementaires.yaml` : C5=0.0453 seul | Shadow billing structurellement biaisé pour profils HP/HC | Écart inexpliqué sur factures HP/HC | — | 5-15% d'écart composante réseau | Ajouter HP/HC au minimum pour C5 dans le catalogue + ventilation kWh | M | **Now** |
| I03 | **S0** | réglementaire | Pas de moteur de reconstitution de facture | Aucun service ne recalcule une facture complète depuis index/courbe | PROMEOS ne peut pas prouver un écart | Client ne sait pas POURQUOI il paie X | Non-auditable | — | Concevoir moteur minimal C5 : fourniture HP/HC + TURPE fixe/variable + accise + CTA + TVA | L | **Now** |
| I04 | **S1** | data | Pas de gestion estimé/réel/régularisation | Aucun champ `is_estimated` sur invoice, pas de type REGULARISATION | Factures de régul traitées comme normales → anomalies fantômes | Faux positifs en cascade | — | Bruit dans les insights | Ajouter `is_estimated` bool + type REGULARISATION dans InvoiceLineType | S | **Now** |
| I05 | **S1** | achat | P10/P90 = facteurs constants hardcodés | `purchase_service.py` : `p10 = total × 0.85`, `p90 = total × 1.20` | Faux sentiment de rigueur quantitative | Décision sur fausses plages | Trompeur commercialement | Potentiel >100k EUR si mauvais choix | vol × prix × σ × √horizon au minimum | M | **Now** |
| I06 | **S1** | math | Prorata = days/30 | `billing_shadow_v2.py` : `prorata_factor = days_in_period / 30.0` | Erreur systématique sur mois de 28 ou 31 jours | Écart 0-10% sur abonnement | — | ~3% en moyenne | `days / calendar.monthrange(year, month)[1]` | XS | **Now** |
| I07 | **S1** | gaz | ATRD7 = taux unique 0.025 EUR/kWh | `tarifs_reglementaires.yaml` : rate unique | Faux pour tout profil non-T1 | Écart >30% possible sur T3/T4 | Non-conforme ATRD7 | 15-35% de la composante distribution gaz | Modéliser T1-T4 avec terme fixe + variable | M | **Next** |
| I08 | **S1** | gaz | Pas de conversion PCS m³→kWh | Aucun champ PCS/coefficient thermique dans MeterReading | Impossible de vérifier la facture gaz | kWh facturés vs kWh réels = incontrôlable | — | Variable | Ajouter PCS sur MeterReading gaz | S | **Next** |
| I09 | **S1** | contrat | Pas d'avenant / clause pass-through | Modèle `EnergyContract` sans champ pass-through ni relation avenant | Contrats dynamiques non modélisables | Client ne voit pas l'évolution de son contrat | — | — | Ajouter `pass_through_items` JSON + modèle Avenant | M | **Next** |
| I10 | **S1** | contrat | Pas de périodes tarifaires (HPH/HCH/HPB/HCB) | `EnergyContract` n'a qu'un `price_ref_eur_per_kwh` unique | Un seul prix par contrat = fiction | Impossible de comparer offres à granularité horaire | — | — | Ajouter `price_schedule_json` ou table PricePeriod dédiée | M | **Next** |
| I11 | **S2** | achat | Pas de courbe forward | `purchase_service.py` utilise uniquement EPEX Spot 30j avg | Stratégie indexée sans référence marché crédible | Recommandation déconnectée du marché réel | — | — | Intégrer au moins EEX Cal Y+1 dans MarketPrice | M | **Next** |
| I12 | **S2** | achat | Risk score hardcodé | Fixe=20, Indexé=55, Spot=80, RéFlex=40 (constantes) | Aucune sensibilité au contexte marché/client | Risque ne change jamais quelles que soient les conditions | Trompeur | — | Paramétrer par volatilité + horizon + profil | S | **Next** |
| I13 | **S2** | backend | Pas de mécanisme de capacité | Aucun modèle, aucun service | Composante facture ignorée (~2-4 EUR/MWh) | Shadow billing sous-estime toujours | — | 2-4% | Ajouter composante capacité en V2 | M | **Later** |
| I14 | **S2** | backend | Pas d'énergie réactive | Aucun champ tg φ / cos φ | Pénalité réactive invisible | Facture incomprise pour industriels | — | 1-5% pour industriels | Hors scope C5 V1, ajouter en V2 | M | **Later** |
| I15 | **S2** | UX | Label "confiance: high" sur calcul approximatif | `ShadowBreakdownCard.jsx` affiche confidence badge | Faux sentiment de fiabilité | Client croit que le calcul est exact | Trompeur | — | Afficher "estimation indicative" tant que moteur non complet | XS | **Now** |
| I16 | **S2** | data | Pas d'ingestion Enedis/GRDF (SGE, Datahub) | Aucun connecteur API réseau | Saisie manuelle = friction d'adoption | Client doit tout importer à la main | — | — | Hors scope V1, roadmap obligatoire affichée | L | **Later** |
| I17 | **S2** | UX | Shadow billing masque ses limites | Affiche 5 composantes mais 3 sont des estimations grossières | Client pense voir un audit comptable | Faux niveau d'expertise affiché | — | Risque réputation | Ajouter disclaimer visible + traçabilité des hypothèses | XS | **Now** |
| I18 | **S3** | facturation | Pas de gestion des avoirs dédiée | Seul `total_eur ≤ 0` dans coverage pour exclure | Avoir = trou dans la couverture ou anomalie fantôme | Insights parasites | — | — | Ajouter type AVOIR dans InvoiceStatus ou flag `is_credit_note` | S | **Next** |
| I19 | **S3** | achat | Pas de campagne d'achat (workflow) | Aucun modèle Campagne/Offre | Impossible de comparer N offres pour même périmètre | Client ne peut pas gérer son cycle achat | — | — | Modèle Campagne + Offre + validation en V2 | L | **Later** |
| I20 | **S3** | audit | Pas de versioning réglementaire avec migration | `tarifs_reglementaires.yaml` versionné mais pas de recalcul automatique | Shadow billing obsolète dès un changement CRE | Calculs faux sans alerte | Réglementaire | Variable | Ajouter alerte "taux expiré" + recalcul batch automatique | M | **Next** |

---

## 6. ANGLES MORTS CRITIQUES

### 6.1 Calcul

- **Aucune reconstitution de facture ligne à ligne** — le shadow billing est un calcul parallèle approximatif, pas un recalcul depuis les données brutes (index, courbe, puissance)
- **Pas de ventilation HP/HC/Pointe/Hiver/Été** — tout est en taux plat, même pour C5 qui a une option HP/HC courante
- **CTA absente** de la décomposition V2 (ni calculée, ni affichée comme composante)
- **Composante de comptage** absente du TURPE (terme fixe facturé mensuellement)
- **Pas de calcul de puissance atteinte** vs souscrite — pas de détection d'inadéquation tarifaire (optimisation puissance)
- **Pas de détection de changement de structure tarifaire** (passage C5→C4 si puissance >36 kVA)

### 6.2 Contrat

- **Pas d'avenant** — un contrat est immuable une fois créé, impossible de tracer les modifications
- **Pas de clause pass-through** modélisée — composantes variables (capacité, CEE, TURPE) non identifiées
- **Pas de périodes tarifaires multiples** par contrat (pointe, HPH, HCH, HPB, HCB)
- **Pas de coefficient de profil/forme** lié au contrat
- **Pas de périmètre multi-sites** dans le contrat (un contrat = un site via FK `site_id`, malgré le N-N via DeliveryPoint)
- **Pas de date de préavis calculée** distincte de la date de fin (le radar la calcule mais le contrat ne la stocke pas)

### 6.3 Data

- **Pas d'index de relève** (début/fin de période) — les kWh viennent de la facture, pas vérifiables indépendamment
- **Pas de PCS gaz** — conversion m³→kWh non traçable
- **Pas de courbe de charge dans le billing** — la courbe existe dans `MeterReading` (730 jours horaires) mais n'est jamais utilisée pour reconstituer une facture
- **Pas de données réseau distinctes** (flux Enedis C5/C4, GRDF) — tout vient de la facture fournisseur, impossible de faire un vrai rapprochement réseau/fournisseur
- **Pas de distinction "facture basée sur estimé" vs "index réel"** — `is_estimated` existe sur MeterReading mais pas sur Invoice/InvoiceLine

### 6.4 UX

- **Pas de vue "pourquoi je paie X" en langage simple** — le shadow billing montre des composantes techniques mais pas d'explication textuelle pour un non-expert
- **Pas de comparaison facture vs facture N-1** sur la même période (existe en graphique agrégé mais pas par ligne)
- **Pas de vue consolidée multi-sites** par composante de coût
- **Pas d'alerte "votre TURPE a changé"** automatique lors d'une évolution réglementaire
- **Le client ne sait pas si sa puissance est optimale** — aucune analyse puissance souscrite vs consommée

### 6.5 Audit Trail

- **Pas de traçabilité formule complète** — le `catalog_trace` dans V2 trace le taux utilisé mais pas le détail du calcul (inputs, intermédiaires, output)
- **Pas de versioning du calcul** — si l'algorithme change, les anciens résultats ne sont pas marqués "calculé avec V2.1"
- **Pas de comparaison "avant/après"** quand un taux réglementaire change
- **Pas de journal des modifications** sur les insights (qui a changé le statut, quand, pourquoi)

### 6.6 Rapprochement Réseau/Fournisseur

- **Le rapprochement actuel est mesuré (MeterReading) vs facturé (Invoice)** — ce n'est PAS un rapprochement réseau/fournisseur (il manque la donnée réseau indépendante)
- **Pas de données réseau distinctes** pour comparer avec la facture fournisseur
- **Pas de détection de "facture basée sur estimé"** qui nécessiterait une régularisation future
- **Pas de suivi des flux R1/R2** (Enedis/GRDF → fournisseur)

### 6.7 Gestion Anomalies

- **Pas de workflow de résolution complet** — BillingInsight a un status (OPEN/ACK/RESOLVED/FALSE_POSITIVE) mais pas de SLA, pas d'escalade, pas de preuve de résolution
- **Pas de catégorisation "responsable"** — l'anomalie est-elle due au fournisseur, au réseau, au client, ou à une erreur de données ?
- **Pas de contentieux** modélisé (litige, réclamation fournisseur, suivi de résolution, montant récupéré)
- **Pas d'historique de fermeture** avec justification obligatoire

### 6.8 Gouvernance Achat

- **Pas de validation multi-niveaux** — qui valide la recommandation d'achat ? Le DAF ? L'acheteur ? Le DG ?
- **Pas de traçabilité décisionnelle** — pourquoi cette stratégie a-t-elle été choisie vs les autres ?
- **Pas de note de décision** générée automatiquement (le wizard PurchaseAssistant le prévoit en step 7 mais le moteur `generateDecisionNote` n'est pas connecté au backend)
- **Pas de comparaison offre réelle vs recommandation** ex-post (backtest)

---

## 7. CIBLE PRODUIT V1 CRÉDIBLE

### Scope exact V1 : "Shadow Billing C5 Électricité + Radar Contrats"

#### Automatisé

- Shadow billing C5 BT avec décomposition complète :
  - Fourniture HP/HC (si applicable, sinon Base)
  - TURPE fixe : gestion (EUR/mois) + comptage (EUR/mois)
  - TURPE variable : soutirage HP/HC (EUR/kWh)
  - Accise (TIEE) : EUR/kWh × volume
  - CTA : 27.04% × (TURPE gestion + comptage) × prorata
  - TVA : 5.5% sur abonnement/CTA, 20% sur le reste
- 14 règles d'anomalie existantes (R1-R14) — fonctionnelles
- Couverture mensuelle avec détection de trous
- Radar de renouvellement contrat avec urgence et notification
- Réconciliation mesuré vs facturé (seuil 10%)
- Explainability : top 3 contributeurs à l'écart avec description FR

#### Manuel

- Import de factures CSV/JSON (existant, fonctionnel)
- Saisie des contrats via formulaire (existant)
- Saisie des index de relève (à ajouter — formulaire simple)
- Vérification et résolution des anomalies (workflow existant)
- Mise à jour des taux réglementaires (YAML éditable)

#### Paramétrable

- Taux réglementaires via YAML versionné (existant, à enrichir avec HP/HC)
- Seuils d'anomalie par client (à ajouter sur Organisation)
- Option tarifaire HP/HC par PDL (à ajouter sur DeliveryPoint)
- Prix contractuels par période tarifaire (à ajouter sur Contract)
- Tolérance de calcul configurable (actuellement hardcodée)

#### Hors scope V1 (explicitement)

- C4/C3/C2/C1 (TURPE multi-composantes complet avec 8 postes horosaisonniers)
- Gaz shadow billing (affichage basique seulement — pas de reconstitution)
- Énergie réactive / dépassement de puissance
- Mécanisme de capacité / CEE
- Ingestion PDF automatique (OCR)
- API Enedis SGE / GRDF Datahub
- Monte Carlo / courbe forward complète
- PPA / structuré / click pricing
- Campagne d'achat avec workflow multi-offres
- Avenant contractuel

---

## 8. BACKLOG DE PREUVES

| # | Hypothèse à valider | Impact si faux | Confiance actuelle | Facilité du test | Preuve attendue | Délai |
|---|---------------------|----------------|--------------------|--------------------|-----------------|-------|
| P1 | Shadow billing C5 (corrigé) à ±5% d'une vraie facture | CRITIQUE | FAIBLE | FACILE | 5 vraies factures C5 importées, recalcul manuel, comparaison avec V2 corrigé | 2 jours |
| P2 | CTA corrigée change le résultat de >2% | ÉLEVÉ | FAIBLE | FACILE | Recalcul CTA = 27.04% × abonnement TURPE sur 5 factures, comparaison avant/après | 1 jour |
| P3 | Le taux TURPE unique crée un écart >10% sur factures HP/HC | ÉLEVÉ | MOYEN | FACILE | Comparer taux moyen pondéré HP/HC vs taux unique sur 3 factures C5 HP/HC | 1 jour |
| P4 | Les recommandations d'achat sont utiles vs courtier | ÉLEVÉ | FAIBLE | MOYEN | Benchmark 3 offres réelles vs recommandation PROMEOS, évaluation par un acheteur énergie | 5 jours |
| P5 | Le coverage engine détecte les vrais trous | MOYEN | ÉLEVÉ | FACILE | Tester sur historique réel 12 mois d'un client multi-sites | 1 jour |
| P6 | L'ATRD gaz plat crée un écart >20% sur profil T3 | ÉLEVÉ | MOYEN | MOYEN | Recalculer 2 factures gaz avec grille ATRD7 officielle T1-T4 | 3 jours |
| P7 | Le prorata days/30 crée des écarts significatifs | MOYEN | ÉLEVÉ | FACILE | Calculer l'écart sur février (28j) et janvier (31j) pour 10 factures | 30 min |
| P8 | Les P10/P90 fixes induisent des décisions erronées | ÉLEVÉ | ÉLEVÉ | MOYEN | Comparer facteurs fixes vs simulation historique EPEX sur 2 ans (prix réels) | 3 jours |
| P9 | Le radar contrat détecte les urgences à temps | MOYEN | ÉLEVÉ | FACILE | Vérifier que tous les contrats expiring <90j sont flaggés red/orange | 1 heure |
| P10 | Les 14 règles d'anomalie ont un taux de faux positifs <20% | ÉLEVÉ | MOYEN | MOYEN | Auditer manuellement 50 insights sur données seed, classifier vrais/faux positifs | 2 jours |

---

## 9. OBJECTION-KILLER

| # | Objection probable | Réponse honnête | Preuve manquante à produire |
|---|--------------------|-----------------|-----------------------------|
| 1 | *"Votre shadow billing ne reconstitue pas ma facture, c'est une multiplication simple"* | **Vrai en V1.** Notre V2 décompose en 5 composantes mais reste approximatif pour les profils HP/HC. Le moteur complet C5 est en cours (CTA, HP/HC, comptage). | Benchmark sur 10 vraies factures C5 avec résultat à ±2% |
| 2 | *"Votre TURPE n'a qu'un seul taux, c'est faux pour mes sites C4"* | **Correct.** V1 cible uniquement le C5 BT. Le C4+ sera couvert en V2 avec décomposition pointe/HPH/HCH/HPB/HCB. C'est explicité dans notre roadmap. | Grille TURPE 7 multi-composantes implémentée et testée sur données C4 réelles |
| 3 | *"Vos P10/P90 ne veulent rien dire, c'est du ×0.85/×1.20 en dur"* | **Admis et en cours de correction.** Nous remplaçons par un modèle paramétrique (volatilité historique EPEX × racine du horizon) dans le sprint en cours. | Modèle stochastique validé sur données historiques EPEX 2023-2025 |
| 4 | *"Votre brique gaz est une copie de l'élec avec d'autres chiffres"* | **Partiellement vrai.** Le gaz est en phase de structuration. Nous recommandons pour l'instant de ne pas utiliser le shadow billing gaz en production. | Moteur gaz avec ATRD7 T1-T4 + conversion PCS + stockage |
| 5 | *"Un courtier fait mieux que votre simulateur d'achat"* | **Aujourd'hui oui, pour la recommandation pure.** Notre valeur est dans la traçabilité, la comparabilité multi-offres, et l'historique — pas dans le conseil seul. Le combo audit+achat est unique. | 3 cas d'usage documentés où PROMEOS a détecté un problème invisible au courtier |
| 6 | *"Comment je sais que vos taux réglementaires sont à jour ?"* | Catalogue versionné avec `valid_from` et source CRE/arrêté. Mais pas encore de mécanisme automatique de mise à jour ni d'alerte d'expiration. C'est dans le backlog. | Alerte automatique "taux expiré" + recalcul batch + changelog visible client |
| 7 | *"Je ne vois pas la CTA dans votre décomposition"* | **Défaut identifié.** La CTA est absente du shadow billing V2. Correction prioritaire : CTA = 27.04% × abonnement TURPE mensuel. Livraison sous 2 semaines. | Composante CTA visible dans la décomposition avec traçabilité |
| 8 | *"Vos anomalies sont des règles simples, pas de l'IA"* | **Vrai et assumé.** Ce sont 14 règles déterministes avec seuils configurables. C'est transparent, auditable, et reproductible. L'IA viendra en V2 pour la détection de patterns cross-sites. | Taux de détection : % d'anomalies confirmées vs faux positifs sur données réelles |
| 9 | *"Comment vous gérez les régularisations et les avoirs ?"* | **On ne les gère pas encore correctement.** Les réguls sont traitées comme des factures normales, ce qui peut créer des faux positifs. Correction planifiée : type REGULARISATION + logique estimé→réel. | Type dédié + logique de chaîne estimé/réel/régul fonctionnelle |
| 10 | *"Votre outil est-il plus utile qu'Excel + mon courtier ?"* | **Pas encore pour la facturation pure.** Mais la combinaison patrimoine + conformité + couverture + anomalies + radar contrats dans un seul cockpit est un tout qu'Excel ne peut pas maintenir à l'échelle multi-sites. | 1 client pilote qui confirme un gain de temps mesurable (heures/mois économisées) |

---

## 10. TOP 5 ACTIONS

| # | Action | Effort | Owner | Deadline |
|---|--------|--------|-------|----------|
| **1** | **Corriger la CTA** : calculer sur assiette part fixe acheminement (`turpe_gestion × prorata_mois`), l'ajouter comme 6ème composante du shadow billing V2, l'afficher dans le frontend `ShadowBreakdownCard` | **S** (2 jours) | Backend | 18 mars 2026 |
| **2** | **Ajouter HP/HC au shadow billing C5** : enrichir `tarifs_reglementaires.yaml` avec taux HP et HC pour C5 BT, utiliser la grille `TOUSchedule` existante pour ventiler les kWh, recalculer fourniture + TURPE variable en HP/HC, afficher la ventilation dans le breakdown | **M** (5 jours) | Backend | 28 mars 2026 |
| **3** | **Remplacer les P10/P90 hardcodés** : calculer la volatilité historique depuis `MarketPrice` (déjà en base EPEX Spot), appliquer `vol × prix × σ × √(horizon/12)` pour bornes réalistes, afficher la méthode et les inputs dans le tooltip | **S** (3 jours) | Backend | 21 mars 2026 |
| **4** | **Corriger le prorata + labels de confiance** : remplacer `days/30` par `days/calendar.monthrange()`, remplacer "confiance: high" par "estimation indicative" dans le frontend, ajouter disclaimer visible sur les limites du calcul | **XS** (0.5 jour) | Backend + Front | 14 mars 2026 |
| **5** | **Benchmark sur 5 vraies factures C5** : importer 5 factures réelles, comparer le shadow billing V2 corrigé (actions 1+2+4) avec le montant réel, documenter les écarts composante par composante, ajuster les seuils si nécessaire | **S** (3 jours) | Produit | 4 avril 2026 |

---

## GRILLE D'ÉVALUATION

| # | Dimension | Note /10 | Justification |
|---|-----------|----------|---------------|
| 1 | Exactitude tarifaire électricité | **3/10** | Taux TURPE plat, CTA absente/fausse, pas de HP/HC, prorata approximatif, pas de comptage |
| 2 | Exactitude tarifaire gaz | **2/10** | ATRD plat, pas de T1-T4, pas de PCS, pas de stockage, copier-coller de l'élec |
| 3 | Robustesse shadow billing / réconciliation | **3/10** | Multiplication simple habillée en V1, V2 existe mais composantes fausses, réconciliation = delta brut mesuré/facturé |
| 4 | Qualité data model | **7/10** | Hiérarchie solide, enums complets, soft delete, audit trail, mais manque avenant/période tarifaire/index/PCS |
| 5 | Gestion contrats et campagnes d'achat | **4/10** | Contrat basique OK, radar OK, mais pas d'avenant, pas de pass-through, pas de campagne, pas de comparateur réel |
| 6 | Explicabilité client | **4/10** | 5 composantes affichées mais calcul faux dessous, "confiance: high" trompeuse, pas de "pourquoi je paie X" en langage simple |
| 7 | Maintenabilité réglementaire | **5/10** | Catalogue versionné = bonne base, mais pas de mécanisme d'alerte/migration automatique, pas de recalcul historique |
| 8 | Scalabilité multi-sites | **6/10** | Architecture multi-tenant OK, scope context OK, portfolio roll-up OK, mais pas de consolidation multi-sites par composante de coût |
| 9 | Différenciation marché | **3/10** | Ni mieux qu'Excel pour le calcul, ni mieux qu'un courtier pour l'achat — la valeur est dans l'intégration patrimoine/conformité qui n'est pas encore prouvée côté billing |
| 10 | Exécutabilité V1 à 2 fondateurs | **4/10** | Scope trop large (gaz + élec + achat + 4 stratégies) pour être crédible à 2 — mieux vaut un C5 élec impeccable |

### Score global : 41/100

### Verdict : NON CRÉDIBLE (< 50)

> La brique "Facturation & Achat" dans son état actuel ne peut pas être présentée à un directeur achats énergie comme un outil expert. Les calculs sont structurellement approximatifs, le gaz est une façade, et le moteur d'achat produit du bruit décoratif.
>
> **La bonne nouvelle** : le data model est solide, l'architecture est propre, et les corrections prioritaires (CTA, HP/HC, prorata, P10/P90) sont réalisables en 2-3 semaines. Un recentrage brutal sur **"C5 électricité impeccable"** peut transformer cette brique en produit défendable.

---

*Fin de l'audit — 11 mars 2026*
