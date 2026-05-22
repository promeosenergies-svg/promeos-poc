# Sémantique CFO — Dissociation counts (urgence) vs sums € (valeur)

> **Statut** : décision cardinale produit. Documentée pour pitch pilote
> HELIOS/MERIDIAN + refacto M3+. Établie M2-6.B.frontend.bis.
>
> **Origine** : M2-6.B.backend ([commit `992b5c79`](https://github.com/promeosenergies-svg/promeos-poc/commit/992b5c79))
> Surprise #5 Phase 1 audit.

## Le constat

Si les `sums_eur_*` filtrent les items `closed` comme les `counts_*`, le total
HELIOS livré au pilote serait **45 700 €** (1 800 € closed exclu = optim
Marseille livrée). L'assertion cardinale du sprint M2-6.B.backend était
**47 500 €**. Donc dissociation explicite assumée.

## La dissociation actée

| Métrique | Périmètre SQL | Vue produit | Justification |
|----------|---------------|-------------|---------------|
| `counts_*` (P0, P1, sans responsable, bloqués, preuvés) | `lifecycle_state != "closed"` | **Urgence opérationnelle** Marie Energy Manager | « Combien d'actions à traiter aujourd'hui ? » |
| `sums_eur_*` + `items_with_impact_known` + `items_total` | TOUS items (closed inclus) | **Portfolio financier** Jean-Marc CFO | « Combien de valeur déjà livrée + pipeline ? » |

## Conséquences UI MV3

- **NarrativeBar Tuile « Décisions P0/P1 » — count** : actions actives uniquement
  (4 items = P0+P1 ouverts).
- **NarrativeBar Tuile « Décisions P0/P1 » — sub-line sum €** : sum P0+P1 sur
  tous lifecycles (47,5 k€ ou similaire selon distribution).
- **Colonne « Impact estimé » Référentiel** : valeur par item, indépendamment
  du lifecycle (chaque ligne est sa propre vérité — pas d'agrégat).
- **EditorialNarrativeBlock** : phrase cardinale **« X actions sur Y portent
  un impact estimé : Z k€ »** où :
  - `X` = `items_with_impact_known` (numérateur transparence)
  - `Y` = `items_total` (dénominateur, all-lifecycle)
  - `Z` = `sums_eur_total` (somme all-lifecycle)

## Pitch CFO — Exemple Marie / Jean-Marc

> **Marie (Energy Manager)** : « Voici les 4 décisions P0/P1 à traiter
> aujourd'hui. »
>
> **Jean-Marc (CFO)** : « Et l'impact financier total ? »
>
> **Marie** : « 47 500 € documenté sur 4 actions, dont 1 800 € déjà livré
> (optim Marseille closed). 5 actions restent sans impact estimé : conformité
> réglementaire (audit Nice, BACS Lyon non concerné), items en cours de
> qualification (3 actions Seed V4). »
>
> **Jean-Marc** : « Et les 1 800 € closed comptent vraiment dans le total ? »
>
> **Marie** : « Oui, c'est de la valeur déjà livrée portfolio. Si on les
> exclut, on perd la lecture cumulée 'gain réalisé + pipeline'. La vue
> urgence (counts) les exclut bien — les 4 décisions à traiter aujourd'hui
> ne contiennent pas l'optim Marseille. Dissociation volontaire. »

## Limitation MV3 connue

Cette dissociation peut surprendre un user habitué aux dashboards
« tout-en-un » où counts et sums obéissent au même filtre. À documenter
dans l'onboarding pilote (M2-6.C UI polish ou support écrit).

## Plan M3+

- **Option A — Convergence** : si pilote confirme l'attente sémantique unique,
  fusion counts/sums sur même périmètre (`active` ou `all` selon préférence).
- **Option B — Filtre UI** : ajouter un toggle « Vue urgence » vs « Vue
  portfolio » pour basculer explicitement entre les 2 sémantiques.
- **Option C — Statu quo** : si pilote confirme la dissociation comme valeur
  métier (probable — cohérent avec le workflow CFO réel : on ne ferme pas
  les actions « gain réalisé », on les capitalise).

Trace backlog : `M3-CFO-SEMANTIC-CONVERGENCE` (à arbitrer post-pilote sur
data réelle d'usage).

## Tests qui pin cette doctrine

- [`test_helios_use_case_a_total_47500`](../../backend/tests/api/test_v4_action_center_summary.py)
  (M2-6.B.backend) — pin total 47 500 € qui INCLUT optim Marseille closed (1 800 €).
- [`test_sum_includes_closed_items_cfo_semantics`](../../backend/tests/api/test_v4_action_center_summary.py)
  (M2-6.B.backend) — pin comportement sums all-lifecycle (closed compte) +
  count_p1 = 0 simultanément sur même item (preuve dissociation).
- [`EditorialNarrativeBlock.test.jsx`](../../frontend/src/pages/action-center-v4/__tests__/EditorialNarrativeBlock.test.jsx)
  (M2-6.B.frontend.bis) — pin phrase « X actions sur Y portent un impact
  estimé : Z k€ » + grammaire FR singulier/pluriel + transparence 0/N.
- [`action_center_v4_money_source_guards.test.js`](../../frontend/src/__tests__/source_guards/action_center_v4_money_source_guards.test.js)
  (`SG_AC_V4_MONEY_01`) — interdit le recalcul FE des sums € (force la
  consommation directe `summary.sums_eur_total`).

## Refs

- Bilan M2-6.B.backend Surprise #5 (commit `992b5c79`)
- Bilan M2-6.B.frontend Q19=C audit Amine (commit `470afd5c`)
- Hotfix M2-6.B.frontend.bis (CE COMMIT)
- BACKLOG_M3 : `M3-CFO-SEMANTIC-CONVERGENCE` (post-pilote)
- Doctrine self-review : [`docs/dev/methode_self_review_pr.md`](../dev/methode_self_review_pr.md)
  (pattern `.bis` immédiat — 3e occurrence après M2-5.9.bis et M2-5.10.bis clôture)
