# Décret tertiaire — Mapping traçable des sources

**Date** : 2026-02-20
**Auteurs** : Équipe PROMEOS
**Statut** : En cours (V1)

---

## Convention

| Colonne | Description |
|---------|-------------|
| Règle | Identifiant de la règle métier implémentée |
| Source | Document réglementaire de référence |
| Page/Section | Localisation dans le document (À CLARIFIER si non extrait) |
| Confiance | high = texte de loi explicite, med = interprétation raisonnable, low = heuristique PROMEOS |
| Statut | OK = implémenté et tracé, À CLARIFIER = nécessite extraction/validation |

---

## Règles implémentées (regops/rules/tertiaire_operat.py)

| Règle | Source | Page/Section | Confiance | Statut |
|-------|--------|--------------|-----------|--------|
| SCOPE_UNKNOWN | Décret n°2019-771 art. 1 | À CLARIFIER (page/section) | high | À CLARIFIER |
| OUT_OF_SCOPE (< 1000 m²) | Décret n°2019-771 art. 1 — seuil d'assujettissement | À CLARIFIER (page/section) | high | À CLARIFIER |
| OPERAT_NOT_STARTED | Arrêté du 10 avril 2020 — plateforme OPERAT | À CLARIFIER (page/section) | high | À CLARIFIER |
| ENERGY_DATA_MISSING | Décret n°2019-771 art. 3 — transmission des consommations | À CLARIFIER (page/section) | high | À CLARIFIER |
| MULTI_OCCUPIED_GOVERNANCE | Décret n°2019-771 art. 4 — parties communes / privatives | À CLARIFIER (page/section) | med | À CLARIFIER |

## Seuils et paramètres (regops/config/regs.yaml)

| Paramètre | Valeur | Source | Page/Section | Confiance | Statut |
|-----------|--------|--------|--------------|-----------|--------|
| scope_threshold_m2 | 1000 | Décret n°2019-771 art. 1 | À CLARIFIER | high | À CLARIFIER |
| attestation_display deadline | 2026-07-01 | Arrêté du 10 avril 2020 | À CLARIFIER | med | À CLARIFIER |
| declaration_2025 deadline | 2026-09-30 | Arrêté du 10 avril 2020 | À CLARIFIER | med | À CLARIFIER |
| penalty non_declaration | 7500 € | Code de la construction art. L174-1 | À CLARIFIER | high | À CLARIFIER |
| penalty non_affichage | 1500 € | Code de la construction art. L174-1 | À CLARIFIER | high | À CLARIFIER |

## Règles à ajouter (V39)

| Règle | Source | Page/Section | Confiance | Statut |
|-------|--------|--------------|-----------|--------|
| EFA_COMPLETENESS | Décret n°2019-771 + Arrêté 2020 — définition de l'EFA | À CLARIFIER (page/section) | med | TODO |
| SURFACE_USAGE_COHERENCE | Arrêté du 10 avril 2020 — catégories d'activité | À CLARIFIER (page/section) | med | TODO |
| RESPONSIBILITY_REQUIRED | Décret n°2019-771 art. 4 — répartition des obligations | À CLARIFIER (page/section) | med | TODO |
| TRAJECTORY_2030 (-40%) | Décret n°2019-771 art. 3 — objectifs de réduction | À CLARIFIER (page/section) | high | TODO |
| TRAJECTORY_2040 (-50%) | Décret n°2019-771 art. 3 | À CLARIFIER (page/section) | high | TODO |
| TRAJECTORY_2050 (-60%) | Décret n°2019-771 art. 3 | À CLARIFIER (page/section) | high | TODO |
| MODULATION_ELIGIBLE | Arrêté du 10 avril 2020 — cas de modulation | À CLARIFIER (page/section) | low | TODO |
| VACANCY_PERIOD | Décret n°2019-771 — périodes d'inoccupation | À CLARIFIER (page/section) | low | TODO |
| RENOVATION_TRIGGER | Arrêté du 10 avril 2020 — rénovation majeure | À CLARIFIER (page/section) | low | TODO |

---

## Documents réglementaires à ingérer dans Memobox

| Document | Type | Domain KB | Statut initial | TODO |
|----------|------|-----------|----------------|------|
| Décret n°2019-771 (texte consolidé) | PDF | conformite/tertiaire-operat | review | TODO: extract_pages_from_pdf |
| Arrêté du 10 avril 2020 (modalités) | PDF | conformite/tertiaire-operat | review | TODO: extract_pages_from_pdf |
| FAQ ADEME — Décret tertiaire | PDF/HTML | conformite/tertiaire-operat | review | TODO: locate source |
| Guide OPERAT — Manuel utilisateur | PDF | conformite/tertiaire-operat | review | TODO: locate source |

---

## À CLARIFIER (actions requises)

1. **Pages/sections exactes** : Tous les mappings ci-dessus indiquent "À CLARIFIER (page/section)" car les PDFs réglementaires n'ont pas encore été ingérés et indexés dans Memobox. Action : ingérer les docs, extraire les sections, mettre à jour ce mapping.

2. **Trajectoire 2030/2040/2050** : Les pourcentages de réduction (-40%/-50%/-60%) sont bien connus mais la méthode de calcul exacte (année de référence, ajustements climatiques, modulations) nécessite extraction détaillée de l'Arrêté du 10 avril 2020.

3. **Modulation** : Les cas de modulation (contraintes techniques, patrimoniales, architecturales, coût disproportionné) sont listés dans l'Arrêté mais les seuils exacts de déclenchement ne sont pas encore extraits. → TODO: extract from Arrêté, sections "modulation".

4. **Vacance** : La définition exacte d'une période de vacance (durée minimale, justificatifs requis) n'est pas encore tracée. → TODO: extract from Décret, article relatif à l'inoccupation.

5. **Multi-occupation** : Les règles de répartition entre propriétaire et locataire(s) pour les parties communes vs privatives nécessitent clarification. Confiance "med" car l'interprétation varie selon les sources.

6. **Données externes V2** : Pour une implémentation complète, il faudra :
   - Récupération automatique des consommations via Enedis/GRDF (API)
   - Données climatiques pour ajustement DJU (Degree-Day Units)
   - Catégories d'activité OPERAT (nomenclature exacte)
   - Valeurs de référence par catégorie (CRef, CRefAbs)
