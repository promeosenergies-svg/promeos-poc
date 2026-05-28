# Cross-check officiel Légifrance — Divergences OPERAT/DEET (2026-05-27)

**Sprint** : `claude/conformite-s1-operat-deet-p0` (Chantier 0)
**Source primaire** : Arrêté du 10 avril 2020 modifié (NOR DEVR2007365A), version consolidée **07/09/2025** (modifié par arrêté du 01/08/2025 NOR ATDL2430864A)
**URL Légifrance** : https://www.legifrance.gouv.fr/loda/id/JORFTEXT000041842389
**Mode** : sources officielles uniquement (Légifrance + textes consolidés). Pas de blog, pas de cabinet de conseil sans recoupement Légifrance.

---

## Synthèse cross-check

| # | Divergence | Statut | Valeur officielle | Article/Annexe | Décision |
|---|---|---|---|---|---|
| D1 | CO2 élec OPERAT 0,064 vs ADEME 0,052 | ✅ **CONFIRMÉ** | **0,064 kgCO2/kWh EF PCI** | Annexe VII, tableau VII-2 | **CODER** |
| D2 | EP élec OPERAT 2,3 vs RE2020 1,9 | ✅ **CONFIRMÉ** | **2,3** (contexte Art. 16 changement source énergétique) | Annexe VII | **CODER** (avec scope strict Art. 16) |
| D4 | Plage année référence + butoir | ✅ **CONFIRMÉ** | Plage **2010-2022** + butoir **30/09/2027** + fallback **1ère année pleine d'exploitation** | Article 3.I | **CODER** |
| D5 | TRI par typologie 30/15/10 | ✅ **CONFIRMÉ** | **30 ans** enveloppe / **15 ans** équipements / **10 ans** systèmes optim+exploitation | Article 11.I | **CODER** |

**Conclusion** : les 4 divergences sont officiellement confirmées par Légifrance. Tous les chantiers du sprint S1 peuvent être codés (rien à reporter en "à clarifier").

---

## D1 — Facteur CO2 électricité OPERAT

### Texte officiel verbatim

**Annexe VII, Tableau VII-2 — Facteur de conversion en gaz à effet de serre (équivalent CO2) de l'énergie finale** (arrêté 10/04/2020 modifié, consolidé 07/09/2025) :

| Énergie | Facteur (kgCO2/kWh EF PCI) |
|---|---|
| **Électricité** | **0,064** |
| Gaz naturel | 0,227 |
| Fioul domestique | 0,324 |
| Bois / biomasse | 0,024 à 0,030 |
| Charbon | 0,385 |
| Réseaux de chaleur / froid | Renvoi à l'arrêté du 15/09/2006 (DPE) |

### Périmètre d'application

- Utilisé exclusivement pour le **reporting OPERAT / DEET** (Décret n°2019-771 + arrêté 10/04/2020).
- **NE PAS confondre** avec le facteur ADEME Base Empreinte V23.6 (0,052 kgCO2/kWh) qui reste valide pour :
  - Bilan GES réglementaire (loi Grenelle, BEGES)
  - CSRD volet ESRS E1 (scope 2 location-based)
  - Comptabilité carbone produit
- Les deux valeurs coexistent légitimement. **Le mélange silencieux est un bug.**

### Référence

- Légifrance arrêté principal : https://www.legifrance.gouv.fr/loda/id/JORFTEXT000041842389
- Article 13.III : "L'évaluation de l'émission de gaz à effet de serre correspondant aux données de consommation d'énergie finale… est établie sur la base des consommations effectives en énergie finale de chaque type d'énergie et de facteurs de conversion en gaz à effet de serre déterminés pour chaque type d'énergie selon le tableau présenté en Annexe VII du présent arrêté."
- Annexe VII : https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000045682100

### Décision

**CODER** : créer constante `EMISSION_FACTORS_OPERAT` séparée dans `backend/config/emission_factors.py`. Conserver `EMISSION_FACTORS` ADEME pour Bilan GES / CSRD. Interdire le mélange silencieux via source-guard.

---

## D2 — Coefficient d'énergie primaire électricité OPERAT

### Texte officiel verbatim

**Annexe VII — Coefficients d'énergie primaire non renouvelable** (contexte Article 16 « changement de source énergétique ») :

| Énergie | Coefficient EP non renouvelable |
|---|---|
| **Électricité** | **2,3** |
| Gaz naturel et énergies fossiles | 1 |
| Bois | 0 |
| Réseaux de chaleur urbaine | 1 - ratio EnR (renvoi arrêté 04/08/2021) |

### Précision périmètre — point critique

L'arrêté DEET utilise **principalement l'énergie finale** (pas l'EP) pour le suivi des consommations annuelles OPERAT. Le coefficient **EP=2,3 est utilisé spécifiquement pour l'Article 16** (cas d'un changement de source énergétique impactant la trajectoire de réduction).

**Autres dispositifs avec coefficient EP électricité distinct** :
- **DPE résidentiel + tertiaire** : EP=2,3 jusqu'au 31/12/2025, puis **EP=1,9 à partir du 01/01/2026** (réforme arrêté 05/07/2024 + arrêté 13/08/2025).
- **RE2020** : EP=2,3 historiquement, basculé à 1,9 selon contextes.

→ **3 valeurs coexistent légitimement** dans le code selon le contexte. Le code actuel a une seule constante `EP_COEFFICIENTS[ELECTRICITY] = 1.9` (vraisemblablement pour RE2020 ou DPE post-2026).

### Référence

- Annexe VII Légifrance : https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000045682100
- Arrêté 13/08/2025 modifiant facteur conversion EP électricité DPE : https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000052134589
- Communiqué ministériel : https://www.ecologie.gouv.fr/presse/evolution-du-calcul-du-dpe-1er-janvier-2026-favoriser-lelectrification-du-chauffage

### Décision

**CODER** avec scope strict : créer constante `EP_OPERAT` ou enrichir `EP_COEFFICIENTS_OPERAT` séparée pour le contexte Art. 16 DEET. Conserver `EP_COEFFICIENTS` actuelle (1,9) avec docstring précisant son usage (RE2020 / DPE 2026+). Documenter la coexistence des 3 valeurs (2,3 DEET Art.16 / 1,9 RE2020+DPE 2026 / 2,58 DPE legacy si présent).

**Précaution** : ne PAS remplacer les usages actuels de `EP_COEFFICIENTS` à l'aveugle — auditer chaque consommateur (`grep`) pour décider du bon scope.

---

## D4 — Plage année de référence + butoir

### Texte officiel verbatim

**Article 3.I de l'arrêté 10/04/2020 modifié** :

> « L'année de référence est comprise **entre 2010 et 2022**, ou correspond à la **première année pleine d'exploitation**. […]
> A défaut de renseignement portant sur l'année de référence avant le **30 septembre 2027**, la consommation de référence correspond à la **consommation de la première année pleine d'exploitation**. »

### Règles dérivées

1. **Plage valide** : année ∈ [2010 ; 2022] (bornes incluses, années pleines uniquement = 12 mois consécutifs).
2. **Cas particulier bâtiment neuf** : « première année pleine d'exploitation » (peut être post-2022).
3. **Date butoir déclaration modulation** : 30/09/2027 sur OPERAT.
4. **Fallback automatique post-butoir** : si pas de déclaration avant 30/09/2027 → consommation de référence = première année pleine d'exploitation (déterminée par OPERAT).

### Référence

- Arrêté Valeurs Absolues IV (14/03/2024) a étendu la plage de 2010-2019 vers **2010-2022** (consolidation 7/09/2025).
- Article 3.I Légifrance : https://www.legifrance.gouv.fr/loda/id/JORFTEXT000041842389
- Trace Software pédagogique (recoupé Légifrance) : https://www.trace-software.com/fr/decret-tertiaire-objectifs-et-annee-de-reference-sur-la-plateforme-operat/

### Décision

**CODER** : remplacer la plage actuelle `[2000 ; 2060]` (trop permissive) par `[2010 ; 2022]` strict, avec exception explicite « première année pleine d'exploitation » (saisie spéciale). Ajouter butoir 30/09/2027 documenté. Pas de fallback silencieux : message FR clair + 422 si année hors plage.

---

## D5 — TRI par typologie (modulation pour disproportion économique)

### Texte officiel verbatim

**Article 11.I de l'arrêté 10/04/2020 modifié** :

La disproportion économique est invocable si le temps de retour sur investissement brut dépasse :

| Typologie travaux | Seuil TRI brut |
|---|---|
| **Rénovations de l'enveloppe** (travaux structuraux) | **30 ans** |
| **Renouvellement des équipements énergétiques** (CVC, ECS, éclairage…) | **15 ans** |
| **Systèmes d'optimisation et d'exploitation** (GTB, BACS, pilotage) | **10 ans** |

### Règles dérivées

- Le test de disproportion économique est fait **par typologie indépendamment** (pas un TRI moyen agrégé global).
- Une action de typologie « GTB » avec TRI 12 ans → disproportion ✅ (>10).
- Une action de typologie « enveloppe » avec TRI 12 ans → pas de disproportion (12 ≤ 30).
- L'agrégation d'actions de typologies différentes nécessite un calcul par typologie + une décision composite (l'arrêté ne précise pas la règle composite — c'est au cas par cas du dossier technique OPERAT).

### Référence

- Article 11.I Légifrance : https://www.legifrance.gouv.fr/loda/id/JORFTEXT000041842389
- Cf. également arrêté Valeurs Absolues IV (14/03/2024) qui n'a pas modifié l'Article 11.

### Décision

**CODER** : refactor `backend/services/tertiaire_modulation_service.py` pour calculer un TRI par typologie. Chaque action / lot d'actions doit déclarer sa typologie (`STRUCTURAL_ENVELOPE` / `ENERGY_EQUIPMENT` / `OPTIMIZATION_SYSTEM`). Sortie : `{typologie, tri_years, seuil_disproportion, is_disproportionate, source_legale}` par typologie + une explication globale.

---

## Sources officielles primaires utilisées

| Document | URL | Date consolidation |
|---|---|---|
| Arrêté 10 avril 2020 (texte principal) | https://www.legifrance.gouv.fr/loda/id/JORFTEXT000041842389 | 07/09/2025 |
| Arrêté 10 avril 2020 Annexe VII (CO2 + EP) | https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000045682100 | 07/09/2025 |
| Arrêté 24 nov 2020 (modification) | https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000042994780 | — |
| Arrêté 13 avril 2022 (Valeurs Absolues I) | https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000045641335 | — |
| Arrêté 28 nov 2023 (Valeurs Absolues III) | https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000048543601 | — |
| Arrêté 14 mars 2024 (Valeurs Absolues IV) | (référencé dans la consolidation) | 14/03/2024 |
| Arrêté 1er août 2025 (NOR ATDL2430864A) | https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000052198856 | 01/08/2025 |
| Arrêté 13 août 2025 (DPE — EP 2,3 → 1,9) | https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000052134589 | 01/01/2026 entrée vigueur |
| Communiqué min. transition écologique DPE 2026 | https://www.ecologie.gouv.fr/presse/evolution-du-calcul-du-dpe-1er-janvier-2026-favoriser-lelectrification-du-chauffage | — |

---

## Verdict cross-check

🟢 **Les 4 divergences D1/D2/D4/D5 sont confirmées par sources officielles Légifrance.**

Le sprint S1 peut procéder à l'implémentation des Chantiers 1 (constantes séparées), 2 (année référence) et 3 (TRI par typologie) sans report en « à clarifier ».

**Précautions** :
- D1/D2 : **ne pas casser ADEME / CSRD / BEGES / RE2020 / DPE** en ajoutant les constantes OPERAT. Chaque consommateur du code actuel doit être audité avant migration.
- D4 : la règle « première année pleine d'exploitation » nécessite un schéma data (champ `first_full_year_of_operation` sur EFA) si pas déjà présent.
- D5 : la typologie d'une action n'est pas forcément encodée — ajouter un enum `TertiaireActionTypology` si absent, avec migration de données nulle (existant ne porte pas la typologie ⇒ statut `unknown` ⇒ pas de disproportion auto).
