# ADR-006: Enedis — Bridge dual-source promoted/legacy

**Date**: 2026-04-12
**Statut**: Accepted
**Sprint**: Sprint 4 — SF5 Integration

---

## Contexte

PROMEOS doit exploiter deux sources de donnees de consommation :

1. **Donnees demo/seed** stockees dans `MeterReading` (historique du POC, `value_kwh` deja agrege)
2. **Donnees Enedis reelles** promues depuis les staging SF1-SF4 vers `meter_load_curve` (SF5), qui stockent de la **puissance instantanee** (`active_power_kw`) et non de l'energie.

Les services analytiques (signature, load profile, benchmark) doivent fonctionner des le jour 1 (demo) **et** basculer sur les donnees reelles des qu'elles sont disponibles, **sans reecriture** et **sans recompilation**.

---

## Probleme

Comment permettre aux services analytiques de consommer transparentement soit les donnees demo, soit les donnees Enedis promues, avec :

- Basculement automatique vers les donnees reelles quand elles existent
- Fallback transparent si la promotion n'a pas encore eu lieu
- Visibilite pour l'utilisateur de la source utilisee
- Zero re-architecture des services existants

---

## Options envisagees

### Option A: Re-ecrire tous les services pour lire `meter_load_curve` directement

- (+) Plus simple, une seule source
- (-) Casse la demo (plus de donnees seed)
- (-) Necessite un backfill de `meter_load_curve` avec des donnees factices
- (-) Perte de la capacite a fonctionner en mode degrade

### Option B: Migration complete des donnees seed vers `meter_load_curve`

- (+) Une seule table queryee
- (-) Perd la semantique puissance vs energie (MeterReading est energie, MLC est puissance)
- (-) Operation destructive et irreversible
- (-) Pas de rollback possible

### Option C: Bridge dual-source avec fallback automatique (choisi)

- Creer un module `data_staging/bridge.py` qui :
  - Query `meter_load_curve` en premier
  - Calcule la couverture (days_covered / period_days)
  - Si >= 50% de couverture, utilise les donnees promues (converties kW -> kWh)
  - Sinon, fallback vers `MeterReading`
  - Retourne la source utilisee (`promoted` / `legacy` / `none`)

---

## Decision

**Option C retenue.** Le bridge est l'unique point d'entree pour toutes les lectures de consommation dans les services analytiques.

### Points cles :

1. **Conversion unite a la lecture** : `E(kWh) = P(kW) * (pas_minutes / 60)` pour les donnees promues.
2. **Seuil de couverture 50%** : evite de basculer prematurement quand seules quelques heures sont disponibles.
3. **Champ `data_source` dans chaque reponse API** : l'utilisateur voit explicitement si les chiffres sont demo ou reels.
4. **Hot-path skip** : flag module-level `_promoted_available` avec TTL 5 min pour eviter de queryer `meter_load_curve` a chaque requete quand elle est vide.
5. **Invalidation cache apres promotion** : `invalidate_promoted_cache()` appele automatiquement par `run_promotion()`.

---

## Consequences

### Positives

- **Zero migration** : la demo continue de fonctionner, les nouveaux clients aussi
- **Basculement transparent** : des qu'un client consent et que SF5 promeut, les services utilisent les vraies donnees
- **Debuggable** : le champ `data_source` dans les reponses permet de tracer quelle source a servi
- **Testable** : les 4 tests `TestBridgeKwhConversion` verifient explicitement la conversion kW/kWh

### Negatives

- **Complexite additionnelle** : 2 chemins de donnees au lieu d'1
- **Risque d'incoherence** : si un site a 50% de donnees promues et 50% legacy, le bridge bascule a 50% mais la reponse peut etre hybride
- **Calcul de couverture coute une query supplementaire** (mitigee par le hot-path skip)

---

## Notes d'implementation

Fichier : `backend/data_staging/bridge.py`

- `get_readings(db, meter_ids, start_dt, end_dt)` : retourne `(list[ReadingRow], source)`
- `_query_promoted()` : convertit kW -> kWh via `pas_minutes / 60`
- `_is_promoted_available()` : check TTL-cached de l'existence de donnees dans `meter_load_curve`
- `invalidate_promoted_cache()` : reset du flag apres un run de promotion

Testes par :
- `tests/test_data_staging.py::TestBridgeKwhConversion` (4 tests unitaires sur la conversion)
- `tests/test_sf5_e2e.py::TestE2ESF5Pipeline::test_bridge_switches_to_promoted_after_promotion` (1 test E2E)

---

## References

- Spec SF5 : `docs/specs/feature-enedis-sge-6-data-staging.md`
- Bug corrige par ce pattern : P0 kW->kWh conversion (Sprint 4 audit)
