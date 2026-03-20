# Socle OPERAT minimal — Cadrage technique

> Date : 2026-03-16
> Statut : Cadrage termine, pret a coder
> Objectif : Consommation de reference + trajectoire -40/-50/-60

---

## Fichiers a modifier/creer

### Nouveaux fichiers

| Fichier | Role |
|---------|------|
| `models/tertiaire.py` (ajout) | Modele `TertiaireEfaConsumption` + champs sur `TertiaireEfa` |
| `services/operat_trajectory.py` (nouveau) | Service calcul trajectoire OPERAT |
| `routes/tertiaire.py` (ajout) | 3 endpoints : declare, validate, history |
| `database/migrations.py` (ajout) | Migration table + colonnes |
| `tests/test_operat_trajectory.py` (nouveau) | Tests trajectoire |

### Fichiers a modifier

| Fichier | Modification |
|---------|-------------|
| `models/__init__.py` | Export TertiaireEfaConsumption |
| `services/operat_export_service.py` L182-208 | Utiliser EfaConsumption au lieu de Site.annual_kwh_total |
| `frontend/src/pages/tertiaire/TertiaireEfaDetailPage.jsx` | Bloc trajectoire minimal |

---

## Data model

### TertiaireEfaConsumption (nouveau)

```
id              INTEGER PK
efa_id          INTEGER FK tertiaire_efa NOT NULL
year            INTEGER NOT NULL
kwh_total       FLOAT NOT NULL >= 0
kwh_elec        FLOAT nullable
kwh_gaz         FLOAT nullable
kwh_reseau      FLOAT nullable
is_reference    BOOLEAN default False
is_normalized   BOOLEAN default False
source          VARCHAR(50) nullable (factures, api, estimation, manuel)
created_at      DATETIME
updated_at      DATETIME

UNIQUE(efa_id, year)
CHECK(kwh_total >= 0)
CHECK(year >= 2000 AND year <= 2060)
```

### Champs ajoutes sur TertiaireEfa

```
reference_year                  INTEGER nullable
reference_year_kwh              FLOAT nullable
trajectory_status               VARCHAR(20) nullable (on_track, off_track, not_evaluable)
trajectory_last_calculated_at   DATETIME nullable
```

---

## Service trajectoire

### Regles metier

```
Objectifs Decret Tertiaire :
  2030 : baseline * 0.60 (reduction -40%)
  2040 : baseline * 0.50 (reduction -50%)
  2050 : baseline * 0.40 (reduction -60%)

Statut :
  on_track     = conso courante <= objectif applicable
  off_track    = conso courante > objectif applicable
  not_evaluable = baseline absente OU conso courante absente

Objectif applicable pour une annee d'observation :
  year >= 2050 → target_2050
  year >= 2040 → target_2040
  year >= 2030 → target_2030
  year < 2030  → target_2030 (reference future)
```

### Retour endpoint validate

```json
{
  "efa_id": 1,
  "observation_year": 2025,
  "baseline": {
    "year": 2019,
    "kwh": 500000,
    "source": "factures"
  },
  "current": {
    "year": 2025,
    "kwh": 320000,
    "source": "api"
  },
  "targets": {
    "2030": 300000,
    "2040": 250000,
    "2050": 200000
  },
  "applicable_target_kwh": 300000,
  "applicable_target_year": 2030,
  "delta_kwh": 20000,
  "delta_percent": 6.7,
  "status": "off_track",
  "is_normalized": false,
  "missing_fields": [],
  "warnings": ["Donnees non normalisees climatiquement"]
}
```

---

## Endpoints

| Methode | Path | Role |
|---------|------|------|
| POST | `/api/tertiaire/efa/{id}/consumption/declare` | Declarer conso annuelle (+ flag reference) |
| GET | `/api/tertiaire/efa/{id}/targets/validate?year=2025` | Calcul trajectoire |
| GET | `/api/tertiaire/efa/{id}/consumption` | Historique consommations |

---

## Refactoring export

`operat_export_service.py` L182-208 :

**Avant :** `Site.annual_kwh_total` comme fallback
**Apres :** `TertiaireEfaConsumption` comme source primaire, `Site.annual_kwh_total` en dernier recours avec warning

Les objectifs 2030/2040/2050 utiliseront `reference_year_kwh` au lieu de `total_kwh` de l'annee courante.

---

## Tests prevus

| Test | Verifie |
|------|---------|
| Creation conso reference valide | Modele + endpoint |
| Refus 2 annees reference meme EFA | Contrainte unicite |
| Calcul trajectoire baseline + courant | Service metier |
| Statut not_evaluable si baseline absente | Garde-fou |
| Statut on_track si conso <= objectif | Regle metier |
| Statut off_track si conso > objectif | Regle metier |
| Export utilise nouvelle source | Refactoring |
| Pas de "conforme" sans baseline | Securite |

---

## Limites apres ce patch

| Limite | Impact | Sprint suivant |
|--------|--------|---------------|
| Pas de normalisation climatique | Comparaisons biaisees | Sprint conformite 2 |
| Pas d'audit-trail conso | Tracabilite limitee | Sprint conformite 2 |
| Pas de workflow modulation | Evenements non approuves | Sprint conformite 3 |
| Pas de depot reel OPERAT | Simulation uniquement | Futur |
| Objectifs hardcodes (0.60/0.50/0.40) | Pas configurable | Si regle change |
