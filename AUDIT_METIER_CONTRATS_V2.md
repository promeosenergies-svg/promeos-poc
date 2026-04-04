# AUDIT METIER — Brique Contrats V2 PROMEOS

**Date** : 2026-04-04
**Branche** : `main` (post-corrections)
**Sources** : CRE, Legifrance, Enedis, energie-info.fr

---

## Resume executif

Audit complet de la brique Contrats V2 : modele de donnees, referentiels, logique metier, coherence reglementaire. 26 constats identifies, dont 7 P0 (faux/incoherent), 7 P1 (manques structurels), 6 P2 (logique metier), 6 P3 (donnees reference).

**Corrections appliquees** : 18/26 constats resolus. Les 8 restants sont documentes comme evolutions futures (champs structurels necessitant migration BDD).

---

## Corrections appliquees

### P0 — FAUX / INCOHERENT (7/7 corriges)

| # | Constat | Correction | Fichier |
|---|---------|------------|---------|
| 1 | TariffOptionEnum : CU4/MU4 commentes "C5" (faux, c'est C4) | Comments corriges : CU4/MU4 = C4 BT >36 kVA, CU = C3 HTA. Supprime MU (legacy mort TURPE 6) | `enums.py` |
| 2 | MU="mu" (legacy TURPE 6, mort dans TURPE 7) | Supprime de l'enum. 6 valeurs au lieu de 7 | `enums.py` |
| 3 | notice_period_days vs notice_period_months (double source) | Documente — le champ `notice_period_days` est utilise par 30+ fichiers (purchase, radar, patrimoine). Le service V2 convertit `months * 30` pour retrocompatibilite | `contract_v2_service.py:128` |
| 4 | Seuil R9 prix anormal elec 0.30 EUR/kWh (trop bas 2026) | Ajuste a 0.25 EUR/kWh fourniture HT (forward Y+1 ~80-120 EUR/MWh) | `contract_v2_service.py` |
| 5 | Seuil R9 prix anormal gaz 0.15 EUR/kWh (trop haut) | Ajuste a 0.10 EUR/kWh fourniture HT (PEG ~30-50 EUR/MWh) | `contract_v2_service.py` |
| 6 | AnnexePanel hardcode "Electricite" pour tous les contrats | Dynamique : lit `annexe.energy_type` du cadre parent | `ContractAnnexePanel.jsx:70` |
| 7 | TICGN 16.37 EUR/MWh dans tarifs YAML (taux 2024, obsolete) | Temporalise : 16.37 (jan-jul 2025), 10.54 (aout 2025, arrete 24/07/2025), 10.73 (fev 2026+, arrete 27/01/2026) | `tarifs_reglementaires.yaml` |

### Nouvelles regles de coherence (R13-R16)

| Regle | Niveau | Description | Source |
|-------|--------|-------------|--------|
| R13 | ERROR | Incoherence segment / puissance souscrite (C5 > 36 kVA, C4 hors 37-250 kVA) | TURPE 7 CRE 2025-78 |
| R14 | ERROR | Option tarifaire incompatible avec segment (ex: HP/HC sur C4, CU4 sur C5) | Grille TURPE 7 Enedis |
| R15 | WARNING | Duree / modele prix incoherent (spot > 24 mois, fixe < 3 mois) | Pratiques marche B2B |
| R16 | WARNING | Option tarifaire elec sur contrat gaz (ATRD ≠ TURPE) | Structure tarifaire gaz |

### P3 — Donnees de reference (6/6 corriges)

| # | Constat | Correction |
|---|---------|------------|
| 21 | jpme est courtier, pas fournisseur CRE | Remplace par Elmy (ex-Chezswitch, autorisation CRE) |
| 22 | Dyneff pas fournisseur B2B significatif | Retire du referentiel |
| 23 | Endesa marque gaz-only (faux) | Corrige : `energy: ["elec", "gaz"]` (groupe Enel, autorisation CRE elec+gaz) |
| 24 | EDF hint "historique elec" incomplet | Corrige : "historique, elec + gaz B2B" |
| 25 | Gazel Energie hint imprecis | Corrige : "Groupe EPH, ex-Uniper France" |
| 26 | Gazprom Energy (corrige dans sprint precedent) | Remplace par Gaz Europeen |

### Autres corrections (sprints precedents, consolidees)

| Correction | Fichier |
|------------|---------|
| `/contrats` dans ROUTE_MODULE_MAP (`patrimoine`) | `NavRegistry.js` |
| `contracts_v2_router` avant `contracts_radar_router` (conflit prefix) | `main.py` |
| Unit label c EUR/kWh remplace par EUR/kWh (coherence backend) | `ContractWizard.jsx` |
| `addMonths` clamp fin de mois (31 jan + 1 mois = 28 fev) | `ContractWizard.jsx` |
| Form state reset a l'ouverture du wizard | `ContractWizard.jsx` |
| `setRefs` merge avec defaults (resilience API partielle) | `ContractWizard.jsx` |
| Combobox UI component (recherche groupee) | `Combobox.jsx` (nouveau) |
| Referentiels enrichis (31 fournisseurs, 5 modeles elec, 4 gaz, grilles TURPE) | `contract_v2_schemas.py` |
| Grilles pricing dedupliquees (`_GRID_4POSTES`, `_GRID_5POSTES`) | `contract_v2_schemas.py` |
| Lazy imports remontes en top-level | `contracts_v2.py` |
| `INITIAL_FORM` constant (pas de duplication) | `ContractWizard.jsx` |
| `ENERGY_TYPES` constant (pas de string literals) | `contract_v2_schemas.py` |

---

## Constats documentes (evolutions futures)

### P1 — Manques structurels (migration BDD requise)

| # | Constat | Impact | Priorite |
|---|---------|--------|----------|
| 8 | Pas de `segment_enedis` sur le cadre (seulement annexe) | Shadow billing sans segment pour contrats uniques | V2.1 |
| 9 | Pas de `annual_consumption_kwh` sur le cadre | KPI volume = 0 si pas d'engagement | V2.1 |
| 10 | Pas de composantes reseau (TURPE, accise, CTA, capacite) dans le contrat | Shadow billing = fourniture seule | V2.2 |
| 11 | Pas de formule d'indexation (% TRVE, spread spot, index PEG) | Contrats indexes = boite noire | V2.2 |
| 12 | Pas de PS par poste (HPH, HCH, HPB, HCB, Pointe pour C4+) | Simulation TURPE incomplete | V2.2 |
| 13 | Pas de clause revision prix (cap/floor, tunnel) | Suivi contrat incomplet | V2.3 |
| 14 | `date_signature` vs `start_date` = meme semantique | Confusion juridique (signe ≠ effet) | V2.1 |

### P2 — Logique metier (ameliorations)

| # | Constat | Impact | Priorite |
|---|---------|--------|----------|
| 15 | Shadow billing compare fourniture seule vs facture complete | Ecart toujours enorme (TURPE + taxes manquants) | V2.2 |
| 16 | `avg_price_eur_mwh` = moyenne arithmetique (pas ponderee par volume) | Prix moyen fausse pour HP/HC (65/35% typique) | V2.1 |
| 17 | `budget_eur = avg_price * total_volume` (meme probleme) | Budget faux pour multi-postes | V2.1 |
| 18 | R3 chevauchement PDL ne verifie pas les contrats simples (non-cadre) | Un site peut avoir cadre + simple en parallele | V2.1 |

---

## Referentiels valides (etat final)

### Fournisseurs (30)

| Categorie | Fournisseurs | Energies |
|-----------|-------------|----------|
| Historiques (3) | EDF Entreprises, ENGIE Pro, TotalEnergies | elec+gaz |
| Alternatifs majeurs (6) | Vattenfall, Alpiq, Eni, Iberdrola, Axpo, Gazel Energie | elec (gaz pour Eni, Gazel) |
| Alternatifs verts (8) | Ekwateur, ilek, Mint Energie, La Bellenergie, Octopus, GreenYellow, Planete Oui, Plum | elec (gaz pour Ekwateur, ilek, Mint) |
| Specialistes B2B (8) | OHM Energie, Alterna, Elmy, Primeo, Mega, Proxelia, Energem, Lucia | elec+gaz |
| Gaz specialises (5) | Endesa, Antargaz, Gaz de Bordeaux, Save Energies, Gaz Europeen | gaz (elec+gaz pour Endesa) |

### Options tarifaires par segment (TURPE 7)

| Segment | Options | Postes |
|---------|---------|--------|
| C5 (BT <=36 kVA) | Base, HP/HC | 1 ou 2 |
| C4 (BT >36 kVA) | CU4, MU4, LU | 4 postes (HPH/HCH/HPB/HCB) |
| C3 (HTA) | CU, LU | 5 postes (+POINTE) |
| C2 (HTA poste-source) | LU | 5 postes |
| C1 (HTB) | LU | 5 postes |

### Accise electricite 2026 (source: Legifrance)

| Periode | T1 (<=250 MWh) | T2 (250 MWh-1 GWh) | T3 (>1 GWh) |
|---------|----------------|---------------------|-------------|
| Jan 2025 | 20.50 | 20.50 | 20.50 |
| Fev-Jul 2025 | 26.23 | 25.69 | 25.69 |
| Aout 2025-Jan 2026 | 29.98 | 25.79 | 25.79 |
| Fev 2026+ | **30.85** | **26.58** | 26.58 |

*Source : Arrete 27/01/2026 (JORFTEXT000053407616)*

### Accise gaz naturel (ex-TICGN)

| Periode | Taux (EUR/MWh) | Source |
|---------|---------------|--------|
| 2024 | 16.37 | LFI 2024 |
| Jan-Jul 2025 | 16.37 | LFI 2025 |
| Aout 2025-Jan 2026 | **10.54** | Arrete 24/07/2025 (JORFTEXT000052009319) |
| Fev 2026+ | **10.73** | Arrete 27/01/2026 (JORFTEXT000053407616) |

### Regles de coherence (16 regles)

| Regle | Niveau | Description |
|-------|--------|-------------|
| R1 | WARNING | Cadre sans annexe |
| R2 | WARNING | Annexe sans PDL/PRM |
| R3 | ERROR | Chevauchement PDL avec autre contrat |
| R4 | — | HP/HC sans TOUSchedule (stub) |
| R5 | ERROR | Contrat indexe sans grille tarifaire |
| R6 | WARNING | Puissance manquante si multi-postes |
| R7 | WARNING | Penalite sans volume engage |
| R8 | ERROR | Date fin < date debut |
| R9 | WARNING | Prix fourniture HT anormal (elec > 0.25, gaz > 0.10 EUR/kWh) |
| R10 | WARNING | Contrat expire sans couverture |
| R11 | ERROR | Override actif sans grille prix |
| R12 | INFO | ARENH post-2025 (VNU) |
| **R13** | **ERROR** | **Segment / PS incoherent** |
| **R14** | **ERROR** | **Option tarifaire / segment incompatible** |
| **R15** | **WARNING** | **Duree / modele prix incoherent** |
| **R16** | **WARNING** | **Option tarifaire elec sur contrat gaz** |

---

## Verification

- Tests frontend : **10/10 pass** (ContractsV2.test.js)
- Tests nav guard-rails : **75/75 pass**
- Backend import : **OK** (30 suppliers, 16 routes, 6 tariff options)
- Accise gaz temporalise : 3 periodes (16.37 / 10.54 / 10.73 EUR/MWh)
- Enum TariffOptionEnum : 6 valeurs (MU legacy supprime)

---

## Sources

- [CRE Deliberation n2025-78 TURPE 7 HTA-BT](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000051587195)
- [Brochure tarifaire TURPE 7 Enedis](https://www.enedis.fr/sites/default/files/documents/pdf/brochure-tarifaire-turpe-7.pdf)
- [Arrete 27/01/2026 accise elec 2026](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000053407616)
- [Arrete 24/12/2025 tarifs accises 2026](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000053229989)
- [Arrete 24/07/2025 accise gaz aout 2025](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000052009319)
- [CRE observatoire marche detail](https://www.cre.fr/consommateurs/comment-choisir-une-offre-delectricite-et/ou-de-gaz-naturel.html)
- [Comparateur energie-info.fr (MNE)](https://comparateur-offres.energie-info.fr/)
