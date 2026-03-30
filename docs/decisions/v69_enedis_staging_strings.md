# ADR V69 — Enedis staging : valeurs brutes en strings

> Date : 2026-03-23
> Contexte : Revue SF1+SF2 feature Enedis SGE (point #9)

---

## Contexte

La table `enedis_flux_mesure` stocke toutes les valeurs extraites des flux XML Enedis en tant que strings brutes :
- `valeur_point` : `String(20)` — pas de conversion en float
- `horodatage` : `String(50)` — pas de conversion en datetime/UTC
- `granularite`, `unite_mesure`, etc. : strings brutes du XML

Cela signifie qu'aucune requête SQL analytique directe n'est possible sur la table staging (pas de `WHERE valeur_point > 500` ni de `WHERE horodatage BETWEEN ...`).

---

## Décision

| ID | Décision | Choix retenu |
|----|----------|--------------|
| D1 | Format des valeurs en staging | Strings brutes — aucune transformation |
| D2 | Exploitation analytique | Déférée à la couche de normalisation |

---

## Rationale

1. **Zero data loss** : les flux Enedis sont la source de vérité réglementaire. Toute conversion (arrondi float, normalisation timezone) risque une perte d'information ou une divergence avec le fichier original.

2. **Auditabilité** : en cas de litige ou d'audit, les données staging doivent être comparables octet par octet avec le XML source. Stocker la valeur brute garantit cette traçabilité.

3. **Séparation des responsabilités** : la couche staging archive fidèlement. La couche normalisation (phase ultérieure) convertit, valide et enrichit. Mélanger les deux dans une même table crée du couplage et complique les reprises.

4. **Robustesse** : si Enedis change un format (ex. ajout de décimales, changement de timezone), le staging continue de fonctionner sans modification. Seule la couche de normalisation doit être adaptée.

---

## Conséquences

- Toute exploitation analytique des données Enedis nécessite la couche de normalisation
- Les dashboards et KPIs ne doivent jamais requêter directement `enedis_flux_mesure`
- La couche de normalisation devra gérer : conversion float, parsing datetime ISO8601, validation de plages, gestion des valeurs manquantes
