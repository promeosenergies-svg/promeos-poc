# DOCTRINE V4 — Classement & Priorisation Centre d'Action

**Version** : **v0.3** (avenant 2026-05-14 · Q37-A+ closure_reasons révisés · cf. §11 Historique)
**Date initiale** : 2026-05-13 · **Avenant v0.3** : 2026-05-14
**Statut** : `Accepted` v0.3 — premier avenant doctrinal versionné du projet PROMEOS V4
**Auteurs** : Amine + Claude (session refonte V4)
**Référence** : Centre d'Action V4 PROMEOS · branche `claude/refonte-sol2`
**ADR à produire ensuite** : ADR-025 (architecture) · ADR-026 (migration) · ADR-027 (sécurité) · ADR-028 (lifecycle) · ADR-029 (evidence + audit trail)

---

## 0. TL;DR exécutif

Le Centre d'Action V4 repose sur **deux axes orthogonaux** qui ne doivent jamais être confondus :

```
AXE 1 — CLASSEMENT (kind)
  → Qu'est-ce que c'est ?
  → Attribut intrinsèque, quasi immuable
  → Détermine le rendu visuel et le CTA primaire
  → 7 valeurs : anomaly · action · decision · signal · evidence_request · deadline · recommendation

AXE 2 — PRIORISATION (priority_score)
  → Quand faut-il s'en occuper ?
  → Calcul dérivé, persisté et recalculable
  → Module l'urgence selon 6 règles métier
  → Bracket : P0 / P1 / P2 / P3
```

Cette séparation interdit qu'une **anomalie critique** soit affichée comme une **action ouverte**, ou qu'une **opportunité à 9 mois** masque une **non-conformité à J-3**.

---

## 1. Position du problème

L'audit 2026-05-13 a relevé **6 vocabulaires de statuts concurrents**, **8+ enums sévérité**, **4 mappings sévérité→priorité parallèles**, et la confusion fondamentale entre **nature d'un objet** (anomalie, action, décision) et **niveau d'urgence** (P0, P1, P2).

Le brief V4 introduit `ActionCenterItem` polymorphique avec `kind`, mais traitait initialement `kind` et `priority` comme co-attributs égaux. **C'est faux**. Ce sont deux axes structurellement distincts qui doivent être documentés, calculés, affichés et testés séparément.

Cette doctrine fige les choix architecturaux **avant** d'écrire le code, **avant** de finaliser les ADR, **avant** d'itérer les maquettes — pour éviter des retours arrière coûteux sur 6 mois.

---

## 2. Les deux axes orthogonaux

### 2.1 — Classement (`kind`)

**Définition** : attribut intrinsèque qui répond à la question **"quelle est la nature métier de cet objet ?"**.

**Propriétés cardinales** :
- **Obligatoire** à la création
- **Validé** contre l'enum strict (7 valeurs)
- **Quasi immuable** : modifiable **uniquement par admin** avec justification, tracée dans l'audit trail comme événement `kind_corrected` (cf. §3.3)
- **Détermine** : le rendu UX (Q7-A) + le CTA primaire par défaut + les filtres possibles
- **Ne dépend pas** du contexte temporel ni des autres items

**Exemple** :
- Une facture EDF avec écart 3 412 € sur la pointe HP = `anomaly` (et le restera, même si elle déclenche ensuite une `action` reliée)
- Le choix d'un prestataire ICPE parmi 3 options = `decision`
- L'obligation de déclarer OPERAT avant le 17/05 = `deadline`

### 2.2 — Priorisation (`priority_score` + `priority_bracket` + `priority_explanation`)

**Définition** : calcul dérivé qui répond à la question **"dans quel ordre traiter ces objets aujourd'hui ?"**.

**Propriétés cardinales** :
- **Dérivé** automatiquement de plusieurs entrées (gravité, impact, délai, confiance, récurrence, owner, blockers, applicabilité réglementaire)
- **Persisté** sur l'item (Q8-C) pour permettre le tri SQL rapide
- **Recalculable** sur événements d'invalidation (cf. §4.3)
- **Explicable** : chaque score doit pouvoir être décomposé en composantes lisibles
- **Sensible au contexte** : un même `kind=recommendation` peut être P0 (échéance APER imminente) ou P3 (opportunité lointaine)

**Bracket** :
- `P0` ≥ 80 → à traiter aujourd'hui
- `P1` 60–79 → à traiter cette semaine
- `P2` 40–59 → à traiter ce mois
- `P3` < 40 → backlog, surveillance

### 2.3 — Règle d'or — l'invariant cardinal

> **Le `kind` détermine ce que l'objet EST.**
> **Le `priority_score` détermine quand on s'en occupe.**
> **Les deux sont indépendants — un P0 recommendation reste une recommandation visuellement.**

Aucun override visuel libre n'est autorisé. Une `anomaly` P3 reste rendue comme une anomalie (badge rouge, icône triangle), pas comme un signal discret. Une `recommendation` P0 reste rendue comme une recommandation (badge étoile, bordure pointillée), pas comme une anomalie.

---

## 3. Les 7 kinds — référentiel doctrinal

### 3.1 Tableau cardinal

| `kind` | Définition | Rendu visuel strict (Q7-A) | CTA primaire | Filtres prioritaires |
|---|---|---|---|---|
| `anomaly` | Écart constaté entre attendu et réel · détection automatique ou manuelle | Card avec **badge ANOMALIE** + icône triangle rouge + cause probable visible | **Investiguer** | sévérité · récurrence · source |
| `action` | Tâche d'exécution opérationnelle avec responsable et échéance | Card classique avec **badge ACTION** + responsable + échéance | **Planifier** (si new) / **Démarrer** (si planned) | lifecycle · owner · domaine |
| `decision` | Choix à arbitrer entre 2 ou plusieurs options comparables | Card avec **badge DÉCISION** + options listées (playbooks) + bordure double | **Arbitrer** | échéance arbitrage · scope |
| `signal` | Détection automatique faible/moyenne confiance, à qualifier | Ligne **compacte faible densité** + **badge SIGNAL** + confiance visible | **Qualifier** | confiance · source · date détection |
| `evidence_request` | Demande de pièce justificative (preuve, devis, RIB) | Card avec **panneau preuve mis en avant** + spec attendue + format | **Ajouter preuve** | échéance preuve · type document |
| `deadline` | Obligation à échéance fixe (déclaration, dépôt, attestation) | Card avec **compte à rebours dominant** + badge ÉCHÉANCE | **Préparer** | échéance · obligation source |
| `recommendation` | Opportunité non obligatoire identifiée par PROMEOS | Card avec **bordure pointillée** + badge RECO étoile + ROI inline | **Adopter** / **Refuser** | gain estimé · effort |

### 3.2 Règle Q7-A — rendu strict par kind

Le rendu visuel est **figé** par kind. Pas de surcharge contextuelle. Les bénéfices :

- **Cognition immédiate** : l'utilisateur reconnaît la nature de l'objet en 1 seconde
- **Cohérence cross-vue** : Pilotage / Référentiel / Drawer / Briefing rendent les mêmes objets pareil
- **Testabilité** : tests snapshot par kind sans combinatoire
- **Documentation simple** : 7 patterns, pas N à M combinaisons

**Anti-pattern** : une anomalie urgente affichée avec le rendu d'une action. **Interdit.**

### 3.3 Immutabilité du kind

`kind` est **quasi immuable** :

- **Création** : `kind` est obligatoire et validé contre `KIND_ENUM`
- **Modification standard** : interdite, même par l'owner
- **Correction admin** : autorisée **uniquement** via endpoint dédié `PATCH /api/action-center/items/{id}/correct-kind` avec :
  - Justification obligatoire (≥ 20 caractères)
  - Trace dans `action_event_log` avec `event_type = "kind_corrected"` + `previous_value` + `new_value` + `actor.role = "admin"`
  - Notification à l'owner précédent

**Pourquoi** : changer le `kind` change le rendu, les filtres, les CTAs et les workflows attendus. Permettre la modification libre = bug sémantique garanti.

### 3.4 Iconographie par kind (spec figée pour les maquettes)

| `kind` | Icône SVG conceptuelle | Couleur dominante (token Sol) |
|---|---|---|
| `anomaly` | Triangle d'alerte | `--sol-refuse-fg` |
| `action` | Check carré | `--sol-ink-700` (neutre) |
| `decision` | Branch / split-node | `--sol-hch-fg` |
| `signal` | Antenne / dot grid | `--sol-ink-500` (dashed) |
| `evidence_request` | Document avec coin plié | `--sol-attention-fg` |
| `deadline` | Sablier | `--sol-afaire-fg` |
| `recommendation` | Étoile à 5 branches | `--sol-calme-fg` (dotted) |

---

## 4. Le score de priorisation — modèle Q8-C

### 4.1 Schéma de données

```typescript
type PriorityScoring = {
  // Score persisté
  priority_score: number;              // 0-100
  priority_bracket: "P0" | "P1" | "P2" | "P3";

  // Explicabilité
  priority_explanation: PriorityExplanation;

  // Versioning et fraîcheur
  score_version: string;               // ex. "v1.0.3" — change si formule change
  score_calculated_at: string;         // ISO 8601 UTC
  score_stale: boolean;                // true si invalidation pending
};

type PriorityExplanation = {
  // Composantes ADR-022 (base héritée)
  components_adr022: {
    severity_points: number;           // / 25
    impact_points: number;             // / 25
    due_date_points: number;           // / 20
  };

  // Extensions V4 (cf. ADR-022 + ext V4)
  components_v4: {
    compliance_risk_points: number;    // / 15
    confidence_points: number;         // / 10
    recurrence_bonus: number;          // / 5
    no_owner_penalty: number;          // / 5  (additif si owner manquant P0/P1)
    evidence_missing_bonus: number;    // / 5
  };

  total_raw: number;                   // somme avant règles
  total_final: number;                 // après application des règles

  // Cardinal : règles déclenchées (traçabilité)
  modulation_rules_applied: ModulationRuleCode[];

  // Justification narrative humaine
  narrative: string;                   // ex. "88/100 — dominé par échéance (J+1)
                                       //       et risque conformité SMÉ.
                                       //       Règle R6 a forcé plancher P1."
};

type ModulationRuleCode = "R1" | "R2" | "R3" | "R4" | "R5" | "R6";
```

### 4.2 Composantes du score

Le score combine **3 composantes ADR-022 héritées** (gravité, impact, délai) + **5 extensions V4** (risque conformité, confiance, récurrence, sans responsable, preuve manquante).

Détail des poids :

| Composante | Plage | Origine |
|---|---|---|
| Gravité (`wG`) | 0-25 | ADR-022 |
| Impact (`wI`) | 0-25 | ADR-022 |
| Délai (`wD`) | 0-20 | ADR-022 |
| Risque conformité | 0-15 | ext. V4 |
| Confiance détection | 0-10 | ext. V4 |
| Récurrence | 0-5 (bonus) | ext. V4 |
| Sans responsable | 0-5 (penalty additive) | ext. V4 (override §5.3) |
| Preuve manquante | 0-5 (bonus) | ext. V4 |

**Total max théorique** : 105/100 (les overrides additifs peuvent pousser au-delà — bornage à 100 final).

### 4.3 Événements d'invalidation

`score_stale` passe à `true` (et recalcul programmé) sur les événements suivants :

```
lifecycle_state_changed
owner_changed
due_date_changed
impact_changed
blocker_added
blocker_removed
evidence_added
evidence_expired
confidence_changed
recurrence_group_updated
regulatory_applicability_changed   ← lien avec ADR-024 moteur d'assujettissement
nightly_priority_refresh           ← cron quotidien 03:00 UTC
```

**Stratégie** :
- Recalcul **synchrone** sur événements high-impact (lifecycle, owner, due_date) → score frais visible immédiatement
- Recalcul **asynchrone** sur événements low-impact (confidence, recurrence) → batch nightly

### 4.4 Job de recalcul nightly

```python
# Pseudo-code
def nightly_priority_refresh(db: Session):
    """
    Cron 03:00 UTC quotidien.
    Recalcule tous les scores marqués stale + tous les items P0/P1 quel que soit leur staleness.
    """
    stale_items = db.query(ActionCenterItem).filter(
        ActionCenterItem.score_stale == True
    ).all()

    p0p1_items = db.query(ActionCenterItem).filter(
        ActionCenterItem.priority_bracket.in_(["P0", "P1"]),
        ActionCenterItem.lifecycle_state != "closed"
    ).all()

    for item in set(stale_items + p0p1_items):
        new_scoring = compute_priority_scoring(db, item)
        item.priority_score = new_scoring.priority_score
        item.priority_bracket = new_scoring.priority_bracket
        item.priority_explanation = new_scoring.priority_explanation
        item.score_calculated_at = utcnow()
        item.score_stale = False
        # Audit trail
        record_event(item, event_type="priority_recalculated", ...)
```

---

## 5. Les 6 règles de modulation — version corrigée

### 5.1 — R1 — Risque réel > sévérité brute

**Énoncé** : le score combine **gravité × impact × délai × confiance × récurrence × owner × blockers**, jamais la sévérité brute seule.

**Effet** : tri par défaut Pilotage / Référentiel = "Risque réel" (= `priority_score` desc).

**Conséquence UI** : aucun item n'est trié uniquement sur sévérité.

### 5.2 — R2 — Conformité proche > opportunité lointaine

**Énoncé** : une obligation réglementaire applicable à échéance proche prime sur une opportunité lointaine, même à impact supérieur.

**Seuils figés** :

| Cas | Bracket forcé |
|---|---|
| Conformité applicable + échéance **dépassée** | **P0** (plancher absolu) |
| Conformité applicable + échéance **< 7 jours** | **P0** (plancher absolu) |
| Conformité applicable + échéance **7–30 jours** | **P1** minimum |
| Opportunité (`recommendation`) sans obligation + échéance > 90 jours | **P2** maximum, sauf impact > 100 k€ validé manuellement |

**Lien avec ADR-024** : "conformité applicable" = la règle réglementaire associée a `status = APPLICABLE` dans `regulatory_applicability_service`. Pas de hardcode.

### 5.3 — R3 — Sans responsable

**Énoncé** : un item P0/P1 sans `owner` se voit attribuer une pénalité additive, et déclenche une escalade SLA.

**Effet sur score** : `no_owner_penalty = +5 points` (additif, peut pousser score > 100).

**SLA** :
- P0 sans `owner` > **24h** → notification au manager du domaine
- P0 sans `owner` > **48h** → escalade Direction Énergie + tag `escalated`
- P1 sans `owner` > **5j** → digest hebdo + tag `assignment_overdue`

**Effet UI** : avatar avec **`?` dashed rouge** + label **"À assigner"**. Forme visuelle obligatoire (cf. spec maquettes).

### 5.4 — R4 — Récurrence — **corrigée**

**Énoncé** : une anomalie ou un signal récurrent **reçoit un bonus de score** et est **rattaché à un `recurrence_group`**. Aucun merge automatique. Aucun masquage.

**Logique** :
1. À la création d'un item, calcul de signature `(domain, source_signature, scope_signature, rolling_window_days=90)`
2. Si une signature identique existe avec ≥ 1 item actif dans la fenêtre → rattachement au `recurrence_group_id` existant
3. Sinon, création d'un nouveau `recurrence_group`
4. **L'item reste visible individuellement** dans Référentiel, mais avec chip **"↻ Ne occurrence sur 90j · Voir les occurrences"**

**Effet sur score** : `recurrence_bonus = +1 par occurrence`, plafonné à `+5 points` (= 5e occurrence ou plus).

**UI** :
- Chip récurrence visible : `↻ 3e occurrence · merger ?` → **mauvais libellé**, à remplacer
- Libellé correct : **`↻ 3e occurrence · Voir les occurrences`** ou **`↻ 5e occurrence · Créer dossier`**
- **Jamais "Fusionner"** pour une récurrence. **Jamais "Merger"** pour une récurrence.

**Bouton d'action** :
- `Voir les occurrences` (action passive)
- `Créer dossier de traitement` (action active — crée un nouvel item `kind=decision` ou `kind=action` qui groupe les N occurrences pour un traitement unique)

### 5.5 — R5 — Confiance faible — **corrigée fortement**

**Énoncé** : une donnée à confiance faible (`confidence < 0.6`) ne doit jamais déclencher d'action automatique irréversible et doit afficher **"À qualifier"**. Mais elle **ne force pas systématiquement P3** — la priorité reste dérivée du contexte.

**Logique corrigée** :

```python
if confidence < 0.6:
    # Effets garantis
    item.next_best_action = "qualify"
    item.ui_label_override = "À qualifier"
    item.disable_automatic_irreversible_actions = True
    item.confidence_points = clamp(confidence_points - 4, 0, 10)  # pénalité points

    # Effets contextuels (PAS de bracket forcé)
    if blocks_compliance_or_billing(item):
        create_signal("data_quality_check", source_item=item.id)

    # NE PAS forcer bracket P3 — laisser le score dériver normalement
```

**Exemple cardinal** :
- Signal `pic baseload nocturne` confiance 0,38 → score bas, P3 OK (cas standard)
- Anomalie BACS échéance dépassée preuve absente confiance 0,55 → reste P1 "À qualifier" (à cause de R2 conformité dépassée), **pas P3 caché**

**UI** :
- Chip jaune dashed `À qualifier · conf 0,55` visible
- CTA primaire devient `Qualifier` (pas `Investiguer` ni `Démarrer`)
- Actions destructives désactivées (Clôturer en `dismissed` → grisé avec tooltip "Qualifier d'abord")

### 5.6 — R6 — Opportunité ne masque pas obligation

**Énoncé** : une obligation réglementaire applicable a **priorité plancher P1**, indépendamment de l'impact d'opportunités concurrentes.

**Logique** :
- `regulatory_applicability_service.status == APPLICABLE` ET domain `conformite` → bracket plancher `P1`
- Si échéance dépassée ou < 7 jours → bracket plancher `P0` (cf. R2)
- Une `recommendation` à 200 k€ d'impact estimé ne peut pas reléguer une `deadline` réglementaire P1 sous elle dans le tri

**Lien avec ADR-024** : dépendance directe au moteur d'assujettissement. Pas de hardcode de "conformité applicable".

---

## 6. Récurrence vs Doublon — Q9-B

### 6.1 Distinction sémantique cardinale

| | Doublon | Récurrence |
|---|---|---|
| **Définition** | Même phénomène, créé en double | Même phénomène, occurrences successives dans le temps |
| **Exemple** | Anomalie R20 facture mai créée 2 fois par bug détection | Anomalie tan φ > 0,4 Toulouse vue 5 mois consécutifs |
| **Verbe action** | **Fusionner** (merger) | **Regrouper** (créer dossier) |
| **Effet data** | Suppression de N-1 items, conservation de 1 item parent | Conservation de N items + 1 `recurrence_group` parent |
| **Affichage UI** | Suggestion "1 doublon détecté · Fusionner ?" | Chip "↻ 5e occurrence · Voir les occurrences" |

### 6.2 Modèle `duplicate_groups`

```typescript
type DuplicateGroup = {
  id: string;
  organisation_id: string;
  representative_item_id: string;    // item parent conservé après fusion
  detected_duplicate_ids: string[];  // items détectés comme doublons
  detection_method: "exact_match" | "fuzzy_match" | "manual";
  detection_signature: string;       // hash (kind, domain, scope, period_short)
  status: "suggested" | "merged" | "dismissed";
  suggested_at: string;
  resolved_at?: string;
  resolved_by?: string;
};
```

**UI** : badge orange "1 doublon détecté · Fusionner ?" sur l'item parent. Modal de fusion liste les enfants et permet review avant action.

### 6.3 Modèle `recurrence_groups`

```typescript
type RecurrenceGroup = {
  id: string;
  organisation_id: string;
  domain: string;                    // "facturation" | "consommation" | ...
  source_signature: string;          // hash du phénomène (code R20, type CUSUM, etc.)
  scope_signature: string;           // hash (site_id, building_id?, meter_id?)
  site_id?: string;
  building_id?: string;
  meter_id?: string;
  first_seen_at: string;
  last_seen_at: string;
  occurrence_count: number;          // nombre d'items rattachés actifs
  rolling_window_days: number;       // 90 par défaut
  representative_item_id: string;    // item "vitrine" (le plus récent ou le plus prioritaire)
  status: "active" | "watching" | "closed";
};
```

**UI** : chip jaune "↻ 5e occurrence · 90j" + CTA `Voir les occurrences` (passive) ou `Créer dossier de traitement` (active).

### 6.4 Doctrine UI — Fusionner vs Regrouper

| Contexte | Verbe affiché | CTA |
|---|---|---|
| Item appartient à `duplicate_group.status = suggested` | **Fusionner** | Visible dans header drawer + bulk toolbar |
| Item appartient à `recurrence_group.occurrence_count ≥ 3` | **Regrouper** ou **Créer dossier** | Visible dans drawer (jamais bulk toolbar) |
| Item sans groupe | **Aucun** | Bouton Fusionner masqué |

**Anti-pattern interdit** : afficher "Fusionner" pour une récurrence. **Bug sémantique majeur.**

---

## 7. Doctrine UI — libellés français + masquage des valeurs techniques

### 7.1 Mapping FR cardinal

Toutes les valeurs visibles en mode standard doivent être **traduites en français**. Les codes techniques restent uniquement en mode audit (cf. §7.2).

**Lifecycle states** :

| Code technique | Label FR standard |
|---|---|
| `new` | Nouveau |
| `triaged` | **Qualifié** |
| `planned` | Planifié |
| `in_progress` | En cours |
| `closed` | Clôturé |

**Closure reasons** (révisés v0.3 · Q37-A+ · cf. ADR-028 §4) :

| Code | Label FR | Note |
|---|---|---|
| `resolved` | Résolu | Problème résolu + preuve vérifiée |
| `dismissed` | Écarté | Faux positif, hors-scope |
| `not_applicable` | Non applicable | Réglementation non-applicable (Q4-A) |
| `merged_duplicate` | Fusionné (doublon) | **v0.3 unifié** : `duplicate` + `merged` (Q9-B doublon strict) |
| `resolved_via_recurrence` | Résolu via récurrence | **v0.3 ajouté Q37-A+** : auto-close cascade `recurrence_group.resolved` (≠ doublon, Q9-B) |
| `expired` | Expiré | SLA dépassé · **IL4 interdit P0/P1 conformite/facturation** (cf. ADR-028) |

**Blockers** :

| Code | Label FR |
|---|---|
| `waiting_evidence` | **Preuve attendue** |
| `waiting_third_party` | **Tiers attendu** |
| `waiting_budget` | **Budget attendu** |
| `waiting_data` | Donnée attendue |
| `waiting_supplier` | Fournisseur attendu |
| `waiting_manager_validation` | Validation manager attendue |
| `waiting_regulatory_confirmation` | Confirmation réglementaire attendue |

**Kinds** (badges UI) :

| Code | Label FR badge |
|---|---|
| `anomaly` | **ANOMALIE** |
| `action` | **ACTION** |
| `decision` | **DÉCISION** |
| `signal` | **SIGNAL** |
| `evidence_request` | **PREUVE** |
| `deadline` | **ÉCHÉANCE** |
| `recommendation` | **RECO** |

**Event types** (audit trail mode standard) :

| Code | Label FR |
|---|---|
| `created` | Créé |
| `state_changed` | **État modifié** |
| `assigned` | Assigné |
| `priority_changed` | Priorité modifiée |
| `blocker_added` | Blocker ajouté |
| `blocker_removed` | Blocker levé |
| `evidence_added` | Preuve ajoutée |
| `evidence_verified` | Preuve vérifiée |
| `closed` | Clôturé |
| `reopened` | Rouvert |
| `merged` | Fusionné |
| `bulk_updated` | Modifié en lot |
| `exported` | Exporté |
| `kind_corrected` | **Type corrigé** (admin) |
| `priority_recalculated` | Score recalculé |

### 7.2 Mode standard vs Mode audit

**Mode standard** (par défaut, tous personas) :
- Affiche uniquement les **labels FR**
- Masque les codes techniques
- Masque les IDs internes
- Masque les versions et hashs

**Mode audit** (toggle dans header user, persona admin uniquement) :
- Affiche les codes techniques **à côté** des labels FR : `Qualifié (triaged)`
- Affiche les IDs : `ACI-2026-05-0234`
- Affiche les versions : `score_version v1.0.3`
- Affiche les hashes `recurrence_group.source_signature`

**UI mode toggle** :

```
Header user dropdown :
  ⚙ Mode audit (codes techniques visibles)
```

État `mode=audit` persisté en `localStorage` + query param `?audit=1` pour partage.

### 7.3 Doctrine d'affichage drawer

**Header du drawer** (corrigé) :

```
[ Action principale dynamique ]  [ Assigner ⌄ ]  [ Plus ⌄ ]

Action principale dynamique = next_best_action calculé par PROMEOS :
  - new          → "Qualifier" (kind=signal) ou "Planifier" (autres)
  - triaged      → "Planifier" ou "Arbitrer" (kind=decision)
  - planned      → "Démarrer"
  - in_progress  → "Marquer comme fait" ou "Demander preuve"
  - closed       → "Rouvrir" (admin uniquement)

Plus ⌄ contient :
  - Bloquer
  - Ajouter preuve
  - Clôturer (si pas déjà closed)
  - Créer dossier de traitement (si recurrence_count ≥ 3)
  - Fusionner (UNIQUEMENT si duplicate_group existe)
  - Historique complet
  - Mode audit (toggle)
```

**Anti-pattern** : afficher Fusionner si pas de duplicate_group → **bouton masqué, pas grisé**.

**Priority explainer enrichi** :

```
[Score 88/100 → P0]

Composantes :
  Gravité          22.5 / 25  (ADR-022)
  Impact           21   / 25  (ADR-022)
  Délai            19   / 20  (ADR-022)
  Risque conformité 12  / 15  (ext V4)
  Confiance         9   / 10  (ext V4)
  Sans responsable  0   / 5   (override)
  Preuve manquante  4.5 / 5   (ext V4)

Règles de modulation appliquées :
  R1 · Risque réel > sévérité brute
  R2 · Conformité proche prioritaire
  R5 · Preuve manquante
  R6 · Conformité applicable → plancher P1

Narrative :
  88/100 → Bracket P0 (seuil ≥ 80).
  Le score est dominé par l'échéance proche (J+1 réglementaire)
  et le risque conformité SMÉ. Aucun override appliqué.
```

**Impact section enrichie** :

Chaque dimension a une **micro-définition tooltip** au survol :

```
Estimé    → "Gain attendu si action exécutée selon scénario recommandé."
À risque  → "Montant non sécurisé par une action démarrée ou une preuve validée."
Sécurisable → "Activable immédiatement, action ready-to-start avec preuves disponibles."
Réalisé   → "Gain constaté après clôture de l'action avec preuves vérifiées."
```

**Playbooks section enrichie** :

Le drawer ne mélange plus présentation et arbitrage. Ajout d'un **bloc décision explicite** au-dessus des scénarios :

```
Décision attendue : Choisir un scénario.
Recommandation PROMEOS : scénario B (Audit + plan pilotage CTA).
Pourquoi : meilleur ratio gain / délai / preuve.

[A · Reporter]     12 k€ CAPEX · 8 k€/an gain    [Démarrer →]
[B · RECOMMANDÉ]   68 k€ CAPEX · 49 k€/an gain   [Lancer →]
[C · Alternative] 320 k€ CAPEX · 78 k€/an gain   [Comparer →]
```

---

## 8. Doctrine d'affichage par vue

### 8.1 Pilotage > Décisions

- Affiche **uniquement** les items lifecycle ∈ {`new`, `triaged`, `planned`, `in_progress`} ET priority ∈ {`P0`, `P1`}
- Items `closed` exclus
- Items `P2`/`P3` exclus (visibles en Référentiel)
- Tri par `priority_score` desc puis `due_date` asc
- Maximum 8-10 items affichés (au-delà → lien "Tout voir dans Référentiel")

### 8.2 Pilotage > Journal

- Affiche le **flux chronologique** des événements `action_event_log` des 7 derniers jours
- Filtre les `event_type` significatifs (pas `priority_recalculated` ni `nightly_priority_refresh` qui polluent)
- Pas de tri par priorité — tri chronologique strict
- Cas d'usage : "qu'est-ce qui s'est passé hier ?"

### 8.3 Référentiel

- Affiche **tous** les items (147 dans la démo HELIOS)
- Filtres avancés : `kind` (cardinal §3) séparé de `priority` / `lifecycle` / `domain` / etc.
- Vue table par défaut, vue Kanban en option (5 colonnes lifecycle)
- Tri configurable, par défaut `priority_score` desc

### 8.4 Detail Drawer

- Overlay 740px, scroll interne
- Header sticky : `next_best_action` dynamique + Assigner + Plus ⌄
- Sections obligatoires (cf. §7.3) : title + status + priority explainer + impact + blockers + evidence + compliance link + meta + links + playbooks + audit trail
- Footer sticky : timestamps + boutons rapides
- Mode audit accessible via toggle user dropdown

### 8.5 Impact Drawer

- Overlay 600-700px, ouvert par bouton "Voir l'impact" de la barre narrative
- Affiche : Impact estimé / sécurisé / réalisé / à risque / perdu / gains bloqués + ROI + sources et formules
- Pas un onglet — **un drawer** (cardinal V4)
- Filtrable par période et périmètre

---

## 9. Tests doctrinaux — checklist

### 9.1 Tests `kind` (Q7-A)

- ✅ Snapshot Playwright par kind : 7 snapshots distincts validés visuellement
- ✅ Test impossibilité de modification kind hors admin endpoint
- ✅ Test audit trail event `kind_corrected` créé sur modification
- ✅ Test CTA primaire correct par kind (table §3.1)

### 9.2 Tests `priority_score` (Q8-C)

- ✅ Test score persisté à la création
- ✅ Test `score_stale=true` sur 12 événements d'invalidation
- ✅ Test recalcul nightly remet `score_stale=false`
- ✅ Test composantes ADR-022 + extensions V4 retournées dans `priority_explanation`
- ✅ Test `modulation_rules_applied` obligatoire si bracket P0/P1

### 9.3 Tests modulation R1-R6

- ✅ **R1** : tri Pilotage = `priority_score` desc, pas sévérité brute
- ✅ **R2** : conformité applicable + J-3 → P0 forcé même si impact faible
- ✅ **R2** : opportunité 200 k€ J-180 → P2 max (sauf override admin)
- ✅ **R3** : P0 sans owner depuis 48h → tag `escalated` + notification
- ✅ **R4** : 3e occurrence d'un phénomène → bonus +3 points + rattachement `recurrence_group`
- ✅ **R4** : aucun merge automatique sur recurrence → vérifier suggestion UI = "Regrouper"
- ✅ **R5** : `confidence < 0.6` → `next_best_action = "qualify"` + actions destructives désactivées
- ✅ **R5** : `confidence < 0.6` ne force PAS `bracket = P3` systématiquement
- ✅ **R5** : BACS échéance dépassée + confidence 0.55 → reste P1 "À qualifier"
- ✅ **R6** : `regulatory_applicability.status == APPLICABLE` → `priority_bracket >= P1`

### 9.4 Tests `recurrence_groups` vs `duplicate_groups` (Q9-B)

- ✅ Tables distinctes existent en DB
- ✅ Aucun foreign key cross entre les deux tables
- ✅ UI : "Fusionner" affiché uniquement si `duplicate_group_id` non null et `status=suggested`
- ✅ UI : "Regrouper" affiché uniquement si `recurrence_group.occurrence_count >= 3`
- ✅ Pas de bouton "Fusionner" sur une récurrence — anti-pattern interdit

### 9.5 Tests libellés FR (§7.1)

- ✅ Mode standard : aucun code technique visible (regex strict sur DOM)
- ✅ Mode audit : codes techniques visibles à côté des labels FR
- ✅ Toggle mode audit fonctionnel et persisté en `localStorage`
- ✅ Tooltip accessibility (aria-label, aria-describedby) sur tous les chips

### 9.6 Tests doctrine drawer (§7.3)

- ✅ Header = 3 boutons max (action principale + assigner + plus)
- ✅ `next_best_action` calculé selon `lifecycle_state` et `kind`
- ✅ Fusionner masqué si pas de duplicate_group
- ✅ Section "Règles de modulation appliquées" présente
- ✅ Tooltips micro-définitions impact présentes

---

## 10. Renvois aux ADR

Cette doctrine est la **source unique** des choix V4. Les ADR la **référencent** sans la dupliquer :

| ADR | Statut | Sections de la doctrine référencées |
|---|---|---|
| **ADR-025** Architecture | **Accepted** (2026-05-14) — voir [`docs/dev/L2_ADR-025_architecture_v4.md`](../dev/L2_ADR-025_architecture_v4.md) — schéma DB 8 tables + 20 indexes + 100 tests | §2 (axes orthogonaux), §3 (kinds), §4 (score model), §8 (vues) |
| **ADR-026** Migration data | **Accepted** (2026-05-14) — voir [`docs/dev/L3_ADR-026_migration_data.md`](../dev/L3_ADR-026_migration_data.md) — manuel de bascule sécurisé · 9 invariants I1-I9 · 7 arbitrages Q19-Q25 · cutover Mois 4 + STOP GATE J+14 | §3.3 (immutabilité kind), §7.1 (mapping FR) |
| **ADR-027** Sécurité org-scoping | **Accepted** (2026-05-14) — voir [`docs/dev/L4_ADR-027_securite_org_scoping.md`](../dev/L4_ADR-027_securite_org_scoping.md) — manuel défensif · 11 invariants IS1-IS11 · 7 arbitrages Q26-Q32 · 8 menaces M1-M8 · IDOR matrix 288 cellules · 50 SG CI custom | §3.3 (endpoint admin correct-kind) |
| **ADR-028** Lifecycle states | **Accepted** (2026-05-14) — voir [`docs/dev/L5_ADR-028_lifecycle_states.md`](../dev/L5_ADR-028_lifecycle_states.md) — manuel comportement item · 11 invariants IL1-IL11 · 7 arbitrages Q33-Q39 · state machine 5 états × 10 transitions · 6 closure_reasons révisés (avenant v0.3 inclus ce commit) · 56 tests planifiés | §7.1 (labels FR · closure_reasons révisés v0.3), §8 (doctrine par vue) |
| **ADR-029** Evidence + audit trail | **Accepted** (2026-05-14) — voir [`docs/dev/L6_ADR-029_evidence_audit_trail.md`](../dev/L6_ADR-029_evidence_audit_trail.md) — manuel des preuves et de la traçabilité · 9 invariants IE1-IE9 · 7 arbitrages Q40-Q46 · 16 event_types × 3 catégories rétention RGPD (compliance 5y / business 3y / system 1y) · 16 schemas Pydantic v1 versionnés · 8 articles CNIL référencés · 40+ tests planifiés · garde-fou cardinal **IE9 magic bytes MIME anti-spoofing** · IE4 matrice rétention alignée v0.3 (`merged_duplicate` 3y ≠ `resolved_via_recurrence` 5y) | §3.3 (`kind_corrected`), §4.3 (events), §7.1 (closure_reasons révisés v0.3 → mapping events ADR-029) |

---

## 11. Historique des versions doctrinales

| Version | Date | Type | Changement | Cardinal | Référence |
|---|---|---|---|---|---|
| **v0.1** | 2026-05-12 | Initiale | Cadrage initial doctrine V4 (5 lifecycle states, 6 closure_reasons, 7 kinds, 6 règles modulation R1-R6) | Amine + Claude | (avant commit doctrine) |
| **v0.2** | 2026-05-13 | Acceptation | Doctrine V4 actée avec 9 arbitrages doctrinaux Q1-Q9 + corrections post stress-tests (R4 récurrence corrigée, R5 confiance faible corrigée, drawer 3 actions, libellés FR mode standard) | Amine | commit `883ac4ae` |
| **v0.3** | 2026-05-14 | **Avenant** | **Évolution Q37-A+ closure_reasons** (cardinal Amine 2026-05-14 · Option B sur anomalie mineure D4 audit Phase 0 L5) :<br>• Unification `duplicate` + `merged` → **`merged_duplicate`** (un item fusionné est nécessairement un doublon · Q9-B)<br>• Ajout **`resolved_via_recurrence`** distinct pour respecter Q9-B (récurrence ≠ doublon)<br>• Note IL4 sur `expired` (interdit P0/P1 conformité/facturation) | Amine | commit L5 (ce commit) · Ref ADR-028 §4 |

**Politique d'évolution** :
- Toute évolution doctrinale = **avenant versionné** (jamais de modification silencieuse)
- Bump version dans header + entrée datée dans cette table
- Référence ADR aval qui acte l'évolution
- Mise à jour synchronisée des ADR aval qui réfèrent à la doctrine (CLAUDE.md + tous les ADR Accepted)
- Premier avenant : v0.2 → v0.3 (2026-05-14 · Option B Q37-A+)

---

## 12. Métadonnées doctrine

```yaml
doctrine_version: "v0.3"
date_initial: "2026-05-13"
date_amendment_v03: "2026-05-14"
status: "Accepted v0.3"
authors:
  - Amine (PROMEOS founder)
  - Claude (architecture co-pilot)
arbitrages:
  Q7: A     # Rendu strict par kind
  Q8: C     # Score persisté + invalidation event-driven
  Q9: B     # Tables séparées duplicate_groups / recurrence_groups
modulation_rules_corrections:
  R4: "Récurrence ne se fusionne pas. Se regroupe."
  R5: "Confiance faible force 'À qualifier' + désactive actions irréversibles. Ne force PAS P3."
ui_corrections:
  drawer_header: "3 actions max au lieu de 6"
  drawer_labels: "100% FR en mode standard"
  blockers: "Preuve attendue / Budget attendu / Tiers attendu"
  merge_vs_group: "Fusionner réservé doublons · Regrouper réservé récurrences"
next_steps:
  - "M1 v0.2 : différenciation kind + chips récurrence + confiance"
  - "M2 v0.2 : badges + libellés FR + actions simplifiées + règles modulation"
  - "M4 : Impact Drawer"
  - "Optionnel M5 : Pilotage > Journal"
  - "L1 audit technique avec doctrine en référence"
  - "ADR-025 → ADR-029 en chaîne"
```

---

**Statut** : `Proposed`. À acter par Amine avant L1 audit technique + maquettes v0.2.

Une fois actée, cette doctrine devient **la référence unique** des 6 mois de refonte V4. Toute modification ultérieure passe par un **avenant doctrinal versionné** (v0.3, v0.4, …) — pas de modification silencieuse.
