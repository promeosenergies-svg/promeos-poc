# ADR-020 — Scoring OPERAT Migration `s_ce_m2`

**Statut** : Accepté (cardinal Sprint C-8)
**Date** : 2026-05-07
**Sprint** : C-8 Phase 0 (post Sprint C-7 audit deep)
**Auteurs** : Sprint C-8 ouverture + audit Phase 7 P1-ARCH-001
**Tracking dette** : `D-Sprint-C7-Scoring-OPERAT-S-CE-M2-Migration-001` P1 ARCH

---

## Contexte

Phase 7.1 Sprint C-7 (commit `f5df8bc4`) a ajouté la colonne `s_ce_m2` au modèle `Site` :
> Surface CE OPERAT — Arrêté 10/04/2020 art. 2-j (NOR LOGL2005904A v15/03/2024).
> "La surface de consommations énergétiques [...] intégrant notamment les surfaces de
> stationnement intérieur et de locaux techniques de l'entité fonctionnelle, au contraire
> de la surface de plancher [SDP]".

3 surfaces distinctes Site cardinal post-Phase 7.1 :
- `surface_m2` = SDP (Surface De Plancher) — Code construction art. R111-22
- `tertiaire_area_m2` = surface tertiaire assujettie OPERAT (sous-périmètre SDP)
- `s_ce_m2` = Surface CE OPERAT (Arrêté 10/04/2020 art. 2-j, typiquement > SDP)

**Audit deep Phase 7 (commit `abdf449f`) — finding P1-ARCH-001** :
> Scoring OPERAT (`backend/regops/scoring.py`) **pas migré** sur `s_ce_m2` Phase 7.1.
> Risque divergence SoT silencieuse (cardinal ADR-016 Pilier 3 Cross-module SoT).

**Diagnostic Sprint C-8 Phase 0** :
- `backend/regops/data_quality_specs.py:9` — `"critical": ["tertiaire_area_m2", "operat_status", "annual_kwh_total"]`
- `backend/regops/config/regs.yaml:22+57` — `- tertiaire_area_m2`
- `backend/regops/rules/dpe_tertiaire.py:67-98` — `getattr(site, "tertiaire_area_m2", None)`
- `backend/regops/versioning.py:29` — `"tertiaire_area_m2": site.tertiaire_area_m2`

**Aucune référence `s_ce_m2` côté `regops/`**. Le scoring conformité utilise exclusivement `tertiaire_area_m2`.

---

## Question

Le scoring OPERAT (calcul intensité énergétique kWh/m², export OPERAT, scoring conformité DT/BACS/APER) doit-il :
- A) Continuer à utiliser `tertiaire_area_m2` exclusivement (statu quo Phase C+)
- B) Migrer entièrement sur `s_ce_m2` (pure Arrêté 10/04/2020 art. 2-j)
- C) Hybride : intensity_kwh_m2 sur `tertiaire_area_m2` (cohérent métier OPERAT déclaratif), export OPERAT sur `s_ce_m2` quand renseigné (cardinal légal art. 2-j)

---

## Décision — Option C (hybride contextuel)

**Cardinal** : conserver `tertiaire_area_m2` comme **dénominateur de scoring** (cohérent OPERAT méthode déclarative ADEME) + **ajouter `s_ce_m2` comme champ d'export OPERAT distinct** (cardinal Arrêté 10/04/2020 art. 2-j).

### Raisons

1. **Méthode OPERAT ADEME 2020-2024** : la déclaration OPERAT utilise la **Surface tertiaire assujettie** (`tertiaire_area_m2`) pour calculer la consommation référence Cabs. Migrer sur `s_ce_m2` sans recalibration Cabs casserait la cohérence référentielle ADEME.

2. **Surface CE art. 2-j (post-2024)** : la Surface CE est **plus large** que SDP (intègre stationnement + locaux techniques). Utiliser `s_ce_m2` comme dénominateur baisserait artificiellement l'intensité énergétique → faux verdict de conformité.

3. **Export OPERAT post-Phase D** : le **format ADEME OPERAT v2** (à venir 2027+) demande `s_ce_m2` explicite. PROMEOS doit pouvoir l'exposer sans casser le scoring rétro-compat.

4. **Cohérence ADR-016 Pilier 3 (Cross-module SoT)** : 1 SoT par concept :
   - `tertiaire_area_m2` = SoT scoring DT/BACS/APER intensity_kwh_m2_tertiaire
   - `s_ce_m2` = SoT export OPERAT déclaration (quand renseigné)

### 4 piliers d'application

#### Pilier 1 — Scoring intensity_kwh_m2 inchangé (statu quo Phase C+)

`backend/regops/rules/dpe_tertiaire.py` + `backend/regops/scoring.py` continuent à utiliser
`tertiaire_area_m2`. **Aucune régression scoring** sur les 8 sites HELIOS/MERIDIAN existants.

#### Pilier 2 — Export OPERAT helper avec fallback

Nouveau helper `regops/operat_export_helpers.py:resolve_surface_for_operat_export(site)` :
```python
def resolve_surface_for_operat_export(site: Site) -> tuple[float, str]:
    """Surface à utiliser pour export OPERAT v2 (post-Arrêté 10/04/2020 art. 2-j).

    Priorité :
    1. site.s_ce_m2 si renseigné → "Surface CE (art. 2-j)"
    2. site.tertiaire_area_m2 fallback → "Surface tertiaire assujettie (legacy)"
    """
    if site.s_ce_m2 is not None:
        return (site.s_ce_m2, "Surface CE (Arrêté 10/04/2020 art. 2-j)")
    return (site.tertiaire_area_m2 or 0.0, "Surface tertiaire assujettie (fallback legacy)")
```

#### Pilier 3 — Data quality specs étendue

`backend/regops/data_quality_specs.py:9` ajout `s_ce_m2` en `optional` (pas critical pour
préserver scoring) :
```python
"DT": {
    "critical": ["tertiaire_area_m2", "operat_status", "annual_kwh_total"],
    "optional": ["is_multi_occupied", "naf_code", "surface_m2", "s_ce_m2"],  # ← +s_ce_m2
}
```

Cardinal : `s_ce_m2` est **optional** car son absence ne bloque pas le scoring (fallback legacy
sur `tertiaire_area_m2`). Quand renseigné, l'export OPERAT v2 prend le précédent.

#### Pilier 4 — Source-guards anti-régression

3 SG cardinaux (Phase 8.1) :
- `tertiaire_area_m2` reste seul dénominateur intensity_kwh_m2 (pas régression scoring)
- `resolve_surface_for_operat_export()` privilégie `s_ce_m2` quand non-NULL
- `data_quality_specs["DT"]["optional"]` inclut `s_ce_m2`

---

## Conséquences

### Positives

- **Aucune régression scoring** : les 8 sites HELIOS/MERIDIAN avec `s_ce_m2 IS NULL` continuent
  à scorer sur `tertiaire_area_m2` (statu quo absolu).
- **Export OPERAT v2 ready** : sites futurs avec `s_ce_m2` renseigné exporteront la Surface CE
  cardinale art. 2-j (vs proxy SDP/tertiaire).
- **ADR-016 Pilier 3 satisfait** : 1 SoT par concept (scoring vs export distincts).
- **Migration progressive** : `s_ce_m2` est `nullable=True` (Phase 7.1) — pas de migration data
  HELIOS/MERIDIAN obligatoire (rétro-compat absolue).

### Négatives

- **Complexité +1** : 2 surfaces distinctes à comprendre côté UI + onboarding Site (saisie).
- **Doctrine onboarding** : guide CFO doit expliquer la distinction (pédagogie OPERAT v2).

### Mitigation

- **TraceTooltip FE Phase 8.3** : exposer 3 termes `OPERAT_SURFACE_SDP_DEFINITION` +
  `OPERAT_SURFACE_TERTIAIRE_DEFINITION` + `OPERAT_SURFACE_CE_DEFINITION` (déjà partiellement
  référencé `OPERAT_SURFACE_CONSO_DEFINITION` Phase 3.5).
- **Onboarding Wizard** : champ `s_ce_m2` optionnel avec tooltip "Si vous avez stationnement
  intérieur ou locaux techniques annexes inclus dans périmètre OPERAT v2 post-2024".

---

## Implémentation Sprint C-8 Phase 8.1

1. Helper `regops/operat_export_helpers.py:resolve_surface_for_operat_export()` (~15 LOC)
2. `regops/data_quality_specs.py:9` étendre `optional` avec `s_ce_m2`
3. Wire helper dans `regops/operat_export_service.py` (export ADEME — vérifier migration)
4. Tests cardinaux (~5 tests) : helper fallback + DT scoring inchangé + data_quality étendue
5. SG anti-régression (~3 SG) : pas de `s_ce_m2` dans scoring intensity + helper résout fallback + tertiaire_area_m2 reste critical

**Effort estimé** : ~1.5 h (vs 1h annoncée audit Phase 7 = +50% pour 4 piliers complets).

**Clôture dette** : `D-Sprint-C7-Scoring-OPERAT-S-CE-M2-Migration-001` P1 ARCH.

---

## Références

- ADR-007 (Org/DP cardinal) — modèle hiérarchique
- ADR-016 Pilier 3 (Cross-module SoT) — 1 SoT par concept
- Phase 7.1 livraison `s_ce_m2` colonne — commit `f5df8bc4`
- Audit deep Phase 7 finding P1-ARCH-001 — `docs/audits/AUDIT_PHASE_7_COMPLET_2026_05_06.md`
- Source légale : Arrêté 10/04/2020 art. 2-j (NOR LOGL2005904A v15/03/2024) — validé regulatory-expert audit Phase 7
- Méthode OPERAT ADEME : `https://operat.ademe.fr/` (référentiel `tertiaire_area_m2`)
