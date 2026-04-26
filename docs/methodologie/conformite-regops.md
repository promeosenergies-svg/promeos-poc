# Méthodologie — Score conformité RegOps

> Référence accessible depuis tout footer Sol §5 (Source · Confiance · Mis à jour).
> Dernière révision : 2026-04-26 (Sprint 1.1bis P0-6).

## Objet

Le **score conformité réglementaire** affiché dans les écrans Sol PROMEOS est calculé par le moteur **RegOps** canonique (`backend/regops/scoring.py`).
Il consolide la situation de chaque site face aux 4 obligations majeures du tertiaire français — Décret Tertiaire, BACS, APER, Audit SMÉ — en un nombre unique entre 0 et 100.

## Pondérations

Le moteur RegOps applique deux profils de pondération, sélectionnés automatiquement selon l'applicabilité de l'audit énergétique au patrimoine :

### Profil 4-frameworks (audit applicable)

Quand au moins un site du patrimoine est assujetti à l'obligation d'audit énergétique (ou audit SMÉ certifié ISO 50001) :

| Framework | Poids |
|---|---|
| Décret Tertiaire | 39 % |
| BACS | 28 % |
| APER | 17 % |
| Audit énergétique / SMÉ | 16 % |

### Profil 3-frameworks (audit non applicable)

Quand aucun site n'est assujetti à l'audit énergétique (entité juridique <250 ETP ou CA <50 M€ et bilan <43 M€) :

| Framework | Poids |
|---|---|
| Décret Tertiaire | 45 % |
| BACS | 30 % |
| APER | 25 % |

Source pondérations : `backend/regops/config/regs.yaml:140-143`.

## Calcul par framework

Chaque framework reçoit un sous-score 0-100 calculé déterministiquement à partir des données patrimoine + déclarations :

- **Décret Tertiaire** : ratio sites conformes (statut `conforme`) sur sites assujettis (>1000 m² tertiaire), pondéré par la trajectoire 2030 (-40 % cible, -50 % 2040, -60 % 2050) et la qualité des déclarations OPERAT.
- **BACS** : présence d'un système de Gestion Technique du Bâtiment (GTB) classe B ou supérieure pour sites tertiaires >290 kW. Décret n°2020-887 + abaissement 70 kW prévu en 2030.
- **APER** : conformité Loi APER (audit énergétique Art. L.233-1, code de l'énergie) cycle 4 ans pour entités obligées.
- **Audit SMÉ / ISO 50001** : statut de l'audit énergétique avant échéance 11 octobre 2026 (Loi 2025-391).

## Score consolidé

```
score = Σ (sous_score_framework × poids_framework)
```

Le résultat est arrondi à l'entier pour affichage. Aucun arrondi à mi-chemin n'est effectué — tous les calculs intermédiaires restent en float pour préserver la précision.

## Fréquence de recalcul

Le score est recalculé à chaque mutation impactante du patrimoine (création/modification de site, déclaration OPERAT, validation BACS, soumission audit énergétique). Un job de recalcul nocturne contrôle l'intégrité.

Le timestamp `updated_at` du footer Sol §5 reflète la dernière exécution réussie.

## Niveaux de confiance

- **Haute** (`high`) : score calculé sur données réelles ingérées et patrimoine complètement assujetti.
- **Moyenne** (`medium`) : score modélisé partiellement à partir d'archetypes ADEME ODP ou estimations patrimoine.
- **Faible** (`low`) : couverture EMS <30 %, archetype non résolu, données déclaratives partielles.

## Sources réglementaires citées

- [Décret n°2019-771](https://www.legifrance.gouv.fr/loda/id/JORFTEXT000038812251/) — obligations Décret Tertiaire et plate-forme OPERAT
- [Décret n°2020-887](https://www.legifrance.gouv.fr/loda/id/JORFTEXT000042126230/) — Building Automation and Control Systems (BACS)
- [Loi APER n°2023-175 art. L.171-4 du code de la construction](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000047296081) — solarisation et audit
- [Loi 2025-391 et Directive UE 2023/1791 EED](https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX%3A32023L1791) — Audit énergétique / SMÉ ISO 50001

## Référence interne

- `backend/regops/scoring.py` — moteur SoT
- `backend/regops/config/regs.yaml` — pondérations versionnées (ParameterStore)
- `backend/services/compliance_score_service.py` — service consommateur
- `backend/services/data_provenance/provenance_service.py` — envelope SCM des endpoints

## Versioning méthodologie

Tout changement de pondération ou de méthode de calcul donne lieu à un commit explicite `feat(regops): bump methodology vN.M` et à une révision de cette page. Les écarts produit (par ex. ajout d'un framework au panier) sont annoncés au moins 30 jours avant entrée en vigueur.
