# ADR-016 v3 — Anti-patterns cumulés Piliers 7+8+9 (Phase D-2.2 cardinal)

**Statut** : Accepté
**Date** : 2026-05-07
**Sprint** : Phase D-2 hotfix Tier 1 + D-2.2 ajustée
**Décideurs** : `architect-helios` + `regulatory-expert` + `code-reviewer` agents SDK
**Révision** : 3.0 (v1 = Piliers 1-6 doctrine cumulée Sprint C-7+C-8+D)

## Contexte

Les audits deep multi-agents Phase C-7 → C-8 → D ont identifié un cumul de
patterns/anti-patterns récurrents qui méritent codification doctrinale dans
ADR-016. Ce document formalise les **3 nouveaux Piliers candidats** (7, 8, 9)
détectés Phase D et applicables aux modules futurs.

## Pilier 7 — Hiérarchies internes via self-FK + ondelete=SET NULL

**Détecté** : Phase D-0 (D6 SousCompteur) + audit Phase D + ADR-D-01.

**Règle** :
> Toute hiérarchie 1:N **interne** à une entité (sous-compteur, sub-action workflow,
> filiale d'une entité juridique) doit être implémentée via :
> 1. Self-FK (`Column(ForeignKey("<own_table>.id", ondelete="SET NULL"))`)
> 2. `nullable=True` (le racine de la hiérarchie a NULL en parent_id)
> 3. `relationship("Self", remote_side=[id], backref="<children>")`
>
> **Jamais via une table de jointure dédiée** (anti-pattern over-engineering).

**Anti-pattern proscrit** :
- Table `compteurs_hierarchy(parent_id, child_id, ...)` au lieu de `compteurs.parent_meter_id`.
- ondelete=CASCADE qui détruit silencieusement les sous-entités à la suppression du parent.

**Détection automatisée** :
```bash
# Self-FK détectée
grep -rn "ForeignKey(\"<own_table>" backend/models/<own_module>.py

# ondelete=CASCADE proscrit pour hiérarchies internes
grep -n "ondelete=\"CASCADE\".*self" backend/models/
```

**Sources** :
- `backend/models/energy_models.py:107` (Meter.parent_meter_id) — pattern référent
- `backend/models/compteur.py:65` (Compteur.sub_meter_of_id Phase D-0)

## Pilier 8 — Self-FK orphelin sans wiring service runtime (anti-pattern)

**Détecté** : Phase D audit deep (architect-helios verdict 95% confidence) → ADR-D-01.

**Règle** :
> Toute self-FK ajoutée à un modèle SoT-onboarding (Compteur, EntitéJuridique, Action)
> DOIT (a) référencer un service runtime équivalent existant OU (b) déclarer un bridge
> explicite vers le SoT runtime (cf. `services/compteur_meter_bridge.py` pattern).
> À défaut, la self-FK est rejetée en revue ADR.

**Anti-pattern proscrit** :
- Self-FK ajoutée sur modèle wizard/onboarding alors qu'un modèle runtime distinct
  existe déjà avec son propre self-FK + services consumers (cas D6 Phase D-0).
- "Différenciateur" annoncé sur la self-FK alors qu'aucun service ne consomme
  effectivement la chaîne d'exploitation.

**Détection automatisée** :
```bash
# Self-FK potentiellement orpheline
grep -rl "ForeignKey.*<self_table>" backend/models | while read f; do
  col=$(grep -oP "(?<=ForeignKey\\(\")[^\"]*" "$f" | head -1)
  if ! grep -rl "$col" backend/services > /dev/null; then
    echo "ORPHAN: $f → $col"
  fi
done
```

**Mitigation pattern obligatoire** : bridge service (`ensure_pair()`) + source-guard
test qui détecte les fichiers qui SET la self-FK orpheline sans wiring du bridge.

**Sources** :
- `backend/services/compteur_meter_bridge.py` (Phase D-2 hotfix Tier 1)
- `backend/tests/source_guards/test_compteur_meter_bridge_source_guards.py`
- `docs/adr/ADR-D-01-meter-compteur-duality.md`

## Pilier 9 — Validator permissif transitoire → Enum strict canonique post-audit

**Détecté** : Phase D-1bis (Sprint D1-B C64 regex permissive) + Phase D-2.2 (Enum FtaCode
strict canonique post-audit CRE).

**Règle** :
> Lorsque la **source réglementaire/canonique** d'un domaine fini (codes FTA, NAF, IBAN, etc.)
> est **incertaine ou inaccessible** au moment du sprint, autoriser un validator
> transitoire **regex permissive** qui :
> 1. Couvre **les vraies valeurs canoniques connues** (ne rejette aucune valeur officielle)
> 2. Rejette les **valeurs aberrantes** (préfixe inconnu, format absurde)
> 3. **Documente explicitement** la transition à figer post-audit officiel
>
> Une fois la source canonique parsée/figée (audit officiel CRE/Légifrance/etc.),
> **migrer vers Enum strict canonique** + validator @validates qui exige
> `value in CANONICAL_VALUES`.
>
> Le passage permissive → strict est **un événement cardinal** à tracer dans une ADR
> dédiée + tests de transition (positif canonique + négatif inventé).

**Pattern de transition** :
1. **Phase N-1 (incertain)** : `re.compile(r"^(<préfixe permissif>)")` + commentaire `Phase N+1: Enum strict`
2. **Phase N (audit officiel)** : audit web search / parsing PDF / consultation experte
3. **Phase N+1 (strict)** : `value in {<canonical_set>}` + `class <Domain>(str, Enum)`
4. **Test de transition** : `test_<domain>_legacy_<invented>_codes_rejected_by_validator`

**Anti-pattern proscrit** :
- Inventer des codes/valeurs non sourcés (cas Phase D-1 BT_HCH_PRO inventé).
- Figer un Enum strict **avant** d'avoir consulté la source officielle (risque
  d'omettre des valeurs canoniques légitimes → faux rejets en prod).
- Garder la regex permissive **après** que la source officielle soit accessible
  (dette technique régulatoire).

**Détection automatisée** :
```bash
# Validators permissifs transitoires à régulariser
grep -rn "regex permissive\|Phase D-2.*Enum strict\|Pilier 9 ADR-016" backend/models/
```

**Sources** :
- `backend/models/patrimoine.py` (validator C64 — permissive Phase D-1bis → strict Phase D-2.2)
- `backend/models/enums.py:FtaCode` (Enum canonique CRE TURPE 7)
- `backend/doctrine/constants.py:CANONICAL_FTA_CODES_TURPE_7` (SoT canonique)
- `docs/audits/AUDIT_CODES_FTA_TURPE7_2026_05_07.md` (audit officiel CRE)

## Récapitulatif Piliers ADR-016 cumulés

| Pilier | Domaine | Phase d'origine | Doc cardinal |
| --- | --- | --- | --- |
| 1 | SoT runtime (consumption_unified, meter_unified, etc.) | C-1 | CLAUDE.md |
| 2 | Helper canonique (resolve_naf_code, resolve_org_id) | C-3 | ADR-007 |
| 3 | Cascade vivante (cascade_recompute_on_change) | C-4 | ADR-007 |
| 4 | Anti-DROP discipline migrations Alembic | C-5 | (cumul 15 épisodes) |
| 5 | DEMO_MODE Option B (validation DB X-Org-Id) | C-7 | ADR-017 |
| 6 | Audit deep multi-agents (6 agents SDK parallèles) | C-7 | (Pilier 6 ADR-016) |
| **7** | **Self-FK hiérarchies internes (ondelete=SET NULL + backref)** | **D-0** | **ADR-016 v3** |
| **8** | **Self-FK orphelin sans wiring runtime (anti-pattern + bridge)** | **D-2** | **ADR-D-01 + ADR-016 v3** |
| **9** | **Validator permissif transitoire → Enum strict canonique post-audit** | **D-1bis → D-2.2** | **ADR-016 v3** |

## Tests de transition Pilier 9 — checklist

Pour toute migration permissive → strict, vérifier :
- [ ] Test positif : valeurs canoniques officielles passent le validator
- [ ] Test négatif : valeurs inventées (legacy avant audit) rejetées
- [ ] Constante doctrine `CANONICAL_<DOMAIN>_VALUES` exposée (SoT)
- [ ] Enum `<Domain>` aligné avec constante doctrine (test d'égalité ensembliste)
- [ ] Audit doc officiel cité (CRE/Légifrance/source primaire) avec URL
- [ ] Pre-audit DB : 0 valeur non-canonique en prod (script de migration data si besoin)

## Liens

- ADR-D-01 : [`docs/adr/ADR-D-01-meter-compteur-duality.md`](ADR-D-01-meter-compteur-duality.md) (Pilier 8 application)
- Audit Phase D : [`docs/audits/AUDIT_PHASE_D_COMPLET_2026_05_07.md`](../audits/AUDIT_PHASE_D_COMPLET_2026_05_07.md)
- Audit codes FTA : [`docs/audits/AUDIT_CODES_FTA_TURPE7_2026_05_07.md`](../audits/AUDIT_CODES_FTA_TURPE7_2026_05_07.md)
- Audit D6 dualité : [`docs/audits/AUDIT_D6_DUALITE_RUNTIME_2026_05_07.md`](../audits/AUDIT_D6_DUALITE_RUNTIME_2026_05_07.md)

**Confidence verdict global** : HIGH (consensus 3 agents SDK + audit officiel CRE).
