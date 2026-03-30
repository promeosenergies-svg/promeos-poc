# Decret tertiaire — Mapping tracable des sources

**Date** : 2026-03-30 (mise a jour Phase 4)
**Auteurs** : Equipe PROMEOS
**Statut** : V2 — references legales completees

---

## Convention

| Colonne | Description |
|---------|-------------|
| Regle | Identifiant de la regle metier implementee |
| Source | Document reglementaire de reference |
| Article | Article exact du texte de loi |
| URL | Lien Legifrance (si disponible) |
| Confiance | high = texte de loi explicite, med = interpretation raisonnable, low = heuristique PROMEOS |
| Statut | OK = implemente et trace, TODO = a implementer |

---

## Regles implementees (regops/rules/tertiaire_operat.py)

| Regle | Source | Article | URL | Confiance | Statut |
|-------|--------|---------|-----|-----------|--------|
| SCOPE_UNKNOWN | Decret n2019-771 du 23/07/2019 | Art. R174-22 du CCH (seuil 1000 m2) | [Legifrance](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000038812251) | high | OK |
| OUT_OF_SCOPE (< 1000 m2) | Decret n2019-771 | Art. R174-22 — assujettissement >= 1000 m2 surface plancher | [Legifrance](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000038812251) | high | OK |
| OPERAT_NOT_STARTED | Arrete du 10 avril 2020 | Art. 3 — declaration sur plateforme OPERAT | [Legifrance](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000041842389) | high | OK |
| ENERGY_DATA_MISSING | Decret n2019-771 | Art. R174-23 — transmission des consommations annuelles | [Legifrance](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000038812251) | high | OK |
| MULTI_OCCUPIED_GOVERNANCE | Decret n2019-771 | Art. R174-24 — repartition obligations proprietaire/locataire | [Legifrance](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000038812251) | med | OK |

## Seuils et parametres (regops/config/regs.yaml)

| Parametre | Valeur | Source | Article | URL | Confiance | Statut |
|-----------|--------|--------|---------|-----|-----------|--------|
| scope_threshold_m2 | 1000 | Decret n2019-771 | Art. R174-22 CCH | [Legifrance](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000038812251) | high | OK |
| attestation_display | 2026-07-01 | Arrete du 10 avril 2020 modifie | Art. 5 — affichage public attestation | [Legifrance](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000041842389) | high | OK |
| declaration_2025 | 2026-09-30 | Arrete du 10 avril 2020 modifie | Art. 3 — echeance declaration annuelle | [Legifrance](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000041842389) | high | OK |
| penalty non_declaration | 7 500 EUR | Code de la construction | Art. L174-1 — sanction administrative | — | high | OK |
| penalty non_affichage | 1 500 EUR | Code de la construction | Art. L174-1 — defaut d'affichage | — | high | OK |
| reduction_2030 | -40% | Decret n2019-771 | Art. R174-23 — objectifs par palier | [Legifrance](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000038812251) | high | OK |
| reduction_2040 | -50% | Decret n2019-771 | Art. R174-23 | [Legifrance](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000038812251) | high | OK |
| reduction_2050 | -60% | Decret n2019-771 | Art. R174-23 | [Legifrance](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000038812251) | high | OK |
| annee_reference | 2010-2020 | Arrete du 10 avril 2020 | Art. 3 — choix de l'annee de reference | [Legifrance](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000041842389) | high | OK |

## BACS

| Parametre | Valeur | Source | Article | URL | Confiance | Statut |
|-----------|--------|--------|---------|-----|-----------|--------|
| BACS seuil tier 1 | > 290 kW CVC | Decret n2020-887 du 20/07/2020 | Art. R175-2 CCH | [Legifrance](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000042121844) | high | OK |
| BACS seuil tier 2 | > 70 kW CVC | Decret n2020-887 modifie | Art. R175-2 — echeance repoussee a 2030 | [Legifrance](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000042121844) | high | OK |
| BACS deadline tier 1 | 2025-01-01 | Decret n2020-887 | Art. R175-2 | [Legifrance](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000042121844) | high | OK |
| BACS deadline tier 2 | 2030-01-01 | Decret n2020-887 modifie (2025) | Art. R175-2 | [Legifrance](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000042121844) | high | OK |
| BACS derogation TRI | > 10 ans | Decret n2020-887 | Art. R175-6 — exemption etude TRI | [Legifrance](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000042121844) | high | OK |

## APER

| Parametre | Valeur | Source | Article | URL | Confiance | Statut |
|-----------|--------|--------|---------|-----|-----------|--------|
| Parking solaire large | >= 10 000 m2 | Loi n2023-175 (APER) du 10/03/2023 | Art. 40 | [Legifrance](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000047294244) | high | OK |
| Parking solaire medium | >= 1 500 m2 | Loi APER | Art. 40 | [Legifrance](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000047294244) | high | OK |
| Toiture ENR | >= 500 m2 | Loi APER | Art. 41 | [Legifrance](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000047294244) | high | OK |
| Coverage minimal | 50% surface | Loi APER | Art. 40 al. 3 | [Legifrance](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000047294244) | high | OK |

## Regles a implementer (backlog)

| Regle | Source | Article | Confiance | Statut |
|-------|--------|---------|-----------|--------|
| EFA_COMPLETENESS | Arrete du 10 avril 2020 | Art. 2 — definition EFA | med | TODO |
| SURFACE_USAGE_COHERENCE | Arrete du 10 avril 2020 | Annexe I — nomenclature OPERAT | med | TODO |
| RESPONSIBILITY_REQUIRED | Decret n2019-771 | Art. R174-24 — repartition obligations | med | TODO |
| MODULATION_ELIGIBLE | Arrete du 10 avril 2020 | Art. 6-2 — dossier de modulation | low | TODO |
| VACANCY_PERIOD | Decret n2019-771 | Art. R174-25 — periodes d'inoccupation | low | TODO |
| RENOVATION_TRIGGER | Arrete du 10 avril 2020 | Art. 4 — renovation majeure | low | TODO |

**Note** : Le jalon 2026 (-25%) n'est PAS un objectif reglementaire au sens strict du decret.
C'est la date de premiere declaration obligatoire sur OPERAT. Le premier objectif de reduction
est -40% en 2030 (art. R174-23).

---

## Documents reglementaires de reference

| Document | Type | URL | Statut |
|----------|------|-----|--------|
| Decret n2019-771 du 23/07/2019 (consolide) | Decret | [Legifrance](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000038812251) | Reference |
| Arrete du 10 avril 2020 (modalites) | Arrete | [Legifrance](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000041842389) | Reference |
| Decret n2020-887 du 20/07/2020 (BACS) | Decret | [Legifrance](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000042121844) | Reference |
| Loi n2023-175 du 10/03/2023 (APER) | Loi | [Legifrance](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000047294244) | Reference |
| Code de la construction (L174-1) | Code | — | Reference |
| FAQ ADEME — Decret tertiaire | Guide | operat.ademe.fr | Consulte |
