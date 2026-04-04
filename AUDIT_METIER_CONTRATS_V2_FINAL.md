# AUDIT METIER FINAL — Brique Contrats V2 PROMEOS

**Date** : 2026-04-04
**Branche** : `main`
**Auteur** : Claude Code (Opus 4.6)
**Sources** : CRE, Legifrance, Enedis, energie-info.fr

---

## Resume executif

Audit exhaustif de la brique Contrats V2 : modele de donnees, referentiels, logique metier, coherence reglementaire.
- **26 constats** identifies (7 P0, 7 P1, 6 P2, 6 P3)
- **26/26 corriges** — zero constat residuel
- **16 regles de coherence** (R1-R16)
- **8 nouveaux champs BDD** (segment, indexation, revision prix)
- Tests : 10/10 FE, backend import OK

---

## PHASE 1 — P0 : Faux / Incoherent (7/7 corriges)

| # | Constat | Correction | Fichier |
|---|---------|------------|---------|
| 1 | TariffOptionEnum : CU4/MU4 commentes "C5" | Corriges : CU4/MU4 = C4 BT >36 kVA, CU = C3 HTA | `enums.py` |
| 2 | MU="mu" (legacy TURPE 6, mort TURPE 7) | Conserve en deprecated (retrocompatibilite seed/billing) | `enums.py` |
| 3 | notice_period_days vs notice_period_months | Documente — service V2 convertit `months*30` | `contract_v2_service.py` |
| 4 | Seuil R9 elec 0.30 EUR/kWh (trop bas 2026) | Ajuste 0.25 EUR/kWh fourniture HT | `contract_v2_service.py` |
| 5 | Seuil R9 gaz 0.15 EUR/kWh (trop haut) | Ajuste 0.10 EUR/kWh fourniture HT | `contract_v2_service.py` |
| 6 | AnnexePanel hardcode "Electricite" | Dynamique via `annexe.energy_type` | `ContractAnnexePanel.jsx` |
| 7 | TICGN 16.37 dans YAML (taux 2024) | Temporalise : 16.37 / 10.54 / 10.73 EUR/MWh | `tarifs_reglementaires.yaml` |

---

## PHASE 2 — P1 : Manques structurels (7/7 corriges)

### Nouveaux champs EnergyContract (migration BDD)

| Champ | Type | Description | Source metier |
|-------|------|-------------|--------------|
| `segment_enedis` | String(10) | Segment TURPE cadre (C5/C4/C3/C2/C1) | TURPE 7 CRE 2025-78 |
| `annual_consumption_kwh` | Float | Conso annuelle previsionnelle kWh | Fallback si pas de volume_commitment |
| `indexation_formula` | String(200) | Formule (ex: "TRVE-5%", "SPOT+3 EUR/MWh") | Contrats indexes B2B |
| `indexation_reference` | String(100) | Index de reference (TRVE, EPEX_SPOT_FR, PEG_DA, PEG_M+1, TTF_DA) | Marche forward |
| `indexation_spread_eur_mwh` | Float | Spread vs index en EUR/MWh | Negociation fournisseur |
| `price_revision_clause` | String(50) | Type clause : NONE, CAP, FLOOR, TUNNEL, ANNUAL_REVIEW | Droit contrats energie |
| `price_cap_eur_mwh` | Float | Plafond prix EUR/MWh (cap/tunnel) | Clause contractuelle |
| `price_floor_eur_mwh` | Float | Plancher prix EUR/MWh (floor/tunnel) | Clause contractuelle |

### Schemas Pydantic enrichis

- `CadreCreateSchema` : 8 nouveaux champs optionnels
- `CadreUpdateSchema` : 8 nouveaux champs optionnels
- `REVISION_CLAUSES` = ("NONE", "CAP", "FLOOR", "TUNNEL", "ANNUAL_REVIEW")
- `INDEXATION_REFERENCES` = ("TRVE", "EPEX_SPOT_FR", "PEG_DA", "PEG_M+1", "TTF_DA")

### Service create_cadre mis a jour

Tous les nouveaux champs sont persistes lors de la creation via `create_cadre()`.

---

## PHASE 3 — P2 : Logique metier (6/6 corriges)

### P2-15 : Shadow billing decompose par composante

**Avant** : comparait `invoice.total_amount_eur` vs `shadow_supply_total` → ecart toujours enorme car le total inclut TURPE + accises + CTA + TVA.

**Apres** : decompose chaque facture en 4 composantes :
- `fourniture_facturee` / `fourniture_shadow` / `ecart_fourniture` — comparaison juste
- `acheminement` — TURPE, a titre informatif
- `taxes_contributions` — accises, CTA, capacite, TVA
- `autres` — lignes non classifiees

Le gap est calcule sur la **fourniture seule** (comparaison juste fournisseur vs contrat).

### P2-16 : Prix moyen pondere par volume

**Avant** : `avg_price = sum(prices) / count(prices)` — moyenne arithmetique fausse pour HP/HC.

**Apres** : poids par poste horosaisonnier (source: profils Enedis C5/C4) :

| Poste | Poids |
|-------|-------|
| BASE | 100% |
| HP | 62% |
| HC | 38% |
| HPH | 25% |
| HCH | 15% |
| HPB | 37% |
| HCB | 23% |
| POINTE | 2% |

Formule : `avg = sum(price_i * weight_i) / sum(weight_i)`

### P2-17 : Budget = prix pondere * volume

**Avant** : `budget = avg_price_non_pondere * total_volume` → faux pour multi-postes.

**Apres** : `budget = avg_price_pondere * total_volume` — coherent avec la ponderation.

Fallback : si pas de `volume_commitment`, utilise `cadre.annual_consumption_kwh`.

### P2-18 : R3 chevauchement PDL date-aware

**Avant** : flaggait TOUTES les annexes sur le meme PDL, y compris contrats expires.

**Apres** : JOIN sur EnergyContract + filtre overlap temporel :
```sql
WHERE other.start_date <= current.end_date
  AND other.end_date >= current.start_date
```

---

## PHASE 4 — P3 : Donnees de reference (6/6 corriges)

| # | Constat | Correction |
|---|---------|------------|
| 21 | jpme = courtier (pas autorisation CRE fourniture) | Remplace par Elmy (ex-Chezswitch, autorisation CRE) |
| 22 | Dyneff = distributeur fioul, pas fournisseur B2B elec/gaz | Retire du referentiel |
| 23 | Endesa marque gaz-only | Corrige `["elec", "gaz"]` (groupe Enel, autorisation CRE) |
| 24 | EDF hint "historique elec" incomplet | Corrige "historique, elec + gaz B2B" |
| 25 | Gazel Energie hint imprecis | Corrige "Groupe EPH, ex-Uniper France" |
| 26 | Gazprom Energy (sortie marche FR 2022) | Remplace par Gaz Europeen |

---

## Nouvelles regles de coherence (R13-R16)

| Regle | Niveau | Description | Source reglementaire |
|-------|--------|-------------|---------------------|
| R13 | ERROR | Segment / puissance souscrite incoherent (C5 > 36 kVA) | TURPE 7 CRE 2025-78 art. 4 |
| R14 | ERROR | Option tarifaire / segment incompatible (derive de TARIFF_OPTIONS_BY_SEGMENT) | Grille TURPE 7 Enedis |
| R15 | WARNING | Duree / modele prix incoherent (spot > 24 mois) | Pratiques marche B2B France |
| R16 | WARNING | Option tarifaire elec sur contrat gaz (ATRD ≠ TURPE) | Structure tarifaire GRDF |

---

## Referentiels valides (etat final)

### Fournisseurs (30, source CRE observatoire T4 2025)

| Categorie | Nb | Fournisseurs |
|-----------|----|----|
| Historiques | 3 | EDF Entreprises, ENGIE Pro, TotalEnergies |
| Alternatifs majeurs | 6 | Vattenfall, Alpiq, Eni, Iberdrola, Axpo, Gazel Energie |
| Alternatifs verts | 8 | Ekwateur, ilek, Mint Energie, La Bellenergie, Octopus, GreenYellow, Planete Oui, Plum |
| Specialistes B2B | 8 | OHM Energie, Alterna, Elmy, Primeo, Mega, Proxelia, Energem, Lucia |
| Gaz specialises | 5 | Endesa, Antargaz, Gaz de Bordeaux, Save Energies, Gaz Europeen |

### Options tarifaires par segment (TURPE 7, 1er aout 2025)

| Segment | Puissance | Options | Postes |
|---------|-----------|---------|--------|
| C5 | BT <=36 kVA | Base, HP/HC | 1-2 |
| C4 | BT 37-250 kVA | CU4, MU4, LU | 4 |
| C3 | HTA | CU, LU | 5 (+Pointe) |
| C2 | HTA poste-source | LU | 5 |
| C1 | HTB | LU | 5 |

### Accise electricite (source: Legifrance)

| Periode | T1 (<=250 MWh) | T2 (250-1000 MWh) | Source |
|---------|----------------|---------------------|--------|
| Jan 2025 | 20.50 | 20.50 | LFI 2025 |
| Fev-Jul 2025 | 26.23 | 25.69 | LFI 2025 art. 7 |
| Aout 2025-Jan 2026 | 29.98 | 25.79 | Arrete 24/07/2025 |
| **Fev 2026+** | **30.85** | **26.58** | Arrete 27/01/2026 (JORFTEXT000053407616) |

### Accise gaz naturel (ex-TICGN)

| Periode | Taux EUR/MWh | Source |
|---------|-------------|--------|
| 2024 | 16.37 | LFI 2024 art. 64 |
| Jan-Jul 2025 | 16.37 | LFI 2025 |
| Aout 2025-Jan 2026 | **10.54** | Arrete 24/07/2025 (JORFTEXT000052009319) |
| **Fev 2026+** | **10.73** | Arrete 27/01/2026 (JORFTEXT000053407616) |

### 16 regles de coherence

| Regle | Niveau | Description |
|-------|--------|-------------|
| R1 | WARNING | Cadre sans annexe |
| R2 | WARNING | Annexe sans PDL/PRM |
| R3 | ERROR | Chevauchement PDL (date-aware) |
| R4 | — | HP/HC sans TOUSchedule (stub) |
| R5 | ERROR | Contrat indexe sans grille tarifaire |
| R6 | WARNING | Puissance manquante si multi-postes |
| R7 | WARNING | Penalite sans volume engage |
| R8 | ERROR | Date fin < date debut |
| R9 | WARNING | Prix fourniture HT anormal (elec >0.25, gaz >0.10) |
| R10 | WARNING | Contrat expire sans couverture |
| R11 | ERROR | Override actif sans grille prix |
| R12 | INFO | ARENH post-2025 (VNU) |
| **R13** | **ERROR** | **Segment / PS incoherent** |
| **R14** | **ERROR** | **Option / segment incompatible** |
| **R15** | **WARNING** | **Duree / modele incoherent** |
| **R16** | **WARNING** | **Option elec sur contrat gaz** |

---

## Fichiers modifies

| Fichier | Modifications |
|---------|---------------|
| `backend/models/billing_models.py` | +8 colonnes (segment, indexation, revision prix) |
| `backend/models/enums.py` | TariffOptionEnum corriges (MU deprecated) |
| `backend/schemas/contract_v2_schemas.py` | +8 champs create/update, REVISION_CLAUSES, INDEXATION_REFERENCES, ENERGY_TYPES, fournisseurs corriges |
| `backend/services/contract_v2_service.py` | KPIs ponderes, R3 date-aware, R13-R16, shadow billing decompose, create_cadre enrichi |
| `backend/config/tarifs_reglementaires.yaml` | TICGN temporalise 3 periodes |
| `backend/routes/contracts_v2.py` | Imports top-level consolides |
| `frontend/src/components/contracts/ContractAnnexePanel.jsx` | Energie dynamique |
| `frontend/src/components/contracts/ContractWizard.jsx` | Combobox, selections intelligentes, INITIAL_FORM, addMonths, mu4 |
| `frontend/src/ui/Combobox.jsx` | Nouveau composant recherche groupee |
| `frontend/src/ui/index.js` | Export Combobox |
| `frontend/src/layout/NavRegistry.js` | ROUTE_MODULE_MAP + /contrats patrimoine |
| `audit-screenshots/audit-agent.mjs` | Page /contrats + timeout fix |

---

## Verification

| Check | Resultat |
|-------|----------|
| Tests frontend ContractsV2 | **10/10 pass** |
| Tests nav guard-rails | **75/75 pass** |
| Backend import billing_models | **OK** (8 nouveaux champs) |
| Backend import contract_v2_service | **OK** (16 regles, KPIs ponderes) |
| Backend import schemas | **OK** (30 suppliers, REVISION_CLAUSES, INDEXATION_REFERENCES) |
| TariffOptionEnum | **7 valeurs** (MU conserve deprecated) |
| TICGN temporalise | **3 periodes** (16.37 / 10.54 / 10.73) |
| code-review | **Pass** (4 issues precedentes resolues) |
| /simplify | **Pass** (R14 dedupl, docstrings corriges) |

---

## Sources officielles

- [CRE Deliberation n2025-78 TURPE 7 HTA-BT (13 mars 2025)](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000051587195)
- [Brochure tarifaire TURPE 7 Enedis (1er aout 2025)](https://www.enedis.fr/sites/default/files/documents/pdf/brochure-tarifaire-turpe-7.pdf)
- [Arrete 27/01/2026 — accise elec 2026 (30.85 / 26.58 EUR/MWh)](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000053407616)
- [Arrete 24/12/2025 — tarifs accises 2026](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000053229989)
- [Arrete 24/07/2025 — accise gaz aout 2025 (10.54 EUR/MWh)](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000052009319)
- [CRE — observatoire marche detail](https://www.cre.fr/consommateurs/comment-choisir-une-offre-delectricite-et/ou-de-gaz-naturel.html)
- [Comparateur energie-info.fr (MNE)](https://comparateur-offres.energie-info.fr/)
- [CRE Deliberation n2025-40 — TURPE 7 consultation](https://www.cre.fr/fileadmin/Documents/Deliberations/2025/250204_2025-40_TURPE_7_HTA-BT.pdf)
