# Maquettes Centre d'Action V4 — north star UX figée

**Version** : v0.2 · v0.3.1 (Pilotage Décisions)
**Date** : 2026-05-13 (déposées 2026-05-14)
**Statut** : `Figées` — aucune modification autorisée sans avenant doctrinal versionné
**Référence doctrinale** : [`docs/doctrine/doctrine_v4_classement_priorisation.md`](../../doctrine/doctrine_v4_classement_priorisation.md) (v0.2)

---

## Index des 5 maquettes

| Fichier | Persona | Section doctrine | Cardinaux UX |
|---|---|---|---|
| [`centre_action_v4_pilotage_decisions_v031.html`](centre_action_v4_pilotage_decisions_v031.html) (~80 KB) | Resp. Énergie | §8.1 Pilotage > Décisions | File prioritaire 5 items · 3 sections (File/Jalons/Surveillance) · Doctrine v0.2 strictement appliquée |
| [`centre_action_v4_detail_drawer_v02.html`](centre_action_v4_detail_drawer_v02.html) (~58 KB) | Resp. Énergie | §7.3 + §8.4 Detail Drawer | Header 3 boutons max · Section "Pourquoi P0·88" + 6 règles modulation · Libellés FR strict |
| [`centre_action_v4_referentiel.html`](centre_action_v4_referentiel.html) (~78 KB) | Resp. Énergie | §8.3 Référentiel | Filtres séparés `kind` (Row 1) vs `priority/lifecycle/domain` (Row 2) · 12 rows démo couvrant 7 kinds |
| [`centre_action_v4_impact_drawer.html`](centre_action_v4_impact_drawer.html) (~40 KB) | DAF + Resp. Énergie | §8.5 Impact Drawer | Verdict cardinal +128 k€ sécurisés / 52 k€ à risque · 6 dimensions strictes · ROI démontré · Trajectoire 12m |
| [`centre_action_v4_pilotage_journal.html`](centre_action_v4_pilotage_journal.html) (~53 KB) | Resp. Énergie + admin | §8.2 Pilotage > Journal | Timeline chronologique 7j · 38 events · 3 day-groups + show-earlier · Filtres par event_type |

---

## Cardinaux UX V4

### Les 7 kinds — référentiel doctrinal §3.1

| Kind | Badge UI | Couleur | CTA primaire |
|---|---|---|---|
| `anomaly` | **ANOMALIE** rouge | refuse-fg | Investiguer |
| `action` | **ACTION** neutre | ink-700 | Planifier / Démarrer |
| `decision` | **DÉCISION** bleu | hch-fg | Arbitrer |
| `signal` | **SIGNAL** dashed | ink-500 | Qualifier |
| `evidence_request` | **PREUVE** ambre | attention-fg | Ajouter preuve |
| `deadline` | **ÉCHÉANCE** orange | afaire-fg | Préparer |
| `recommendation` | **RECO** dotted vert | calme-fg | Adopter / Refuser |

### Les 4 brackets de priorité

- `P0` ≥ 80 → aujourd'hui (rouge)
- `P1` 60-79 → cette semaine (ambre)
- `P2` 40-59 → ce mois (vert calme)
- `P3` < 40 → backlog (gris)

### Les 6 règles de modulation R1-R6

- `R1` Risque réel > sévérité brute
- `R2` Conformité proche > opportunité lointaine
- `R3` Sans responsable → escalade SLA
- `R4` Récurrence → bonus + recurrence_group (jamais merge auto)
- `R5` Confiance < 0.6 → "À qualifier" + actions destructives off (ne force PAS P3)
- `R6` Conformité applicable → plancher P1 minimum

---

## Règle anti-modification

Ces maquettes sont la **référence visuelle figée pour 6 mois** (Mois 1-6 V4). Toute modification ultérieure passe par un **avenant doctrinal versionné** (v0.3, v0.4, …) avec production d'une nouvelle maquette numérotée (M1_v04.html, etc.) — la maquette précédente reste conservée pour traçabilité.

Anti-pattern interdit : modifier silencieusement une maquette existante sans bump de version.

---

## Lien retour vers doctrine

Cette doctrine est la **source unique** des choix V4. Voir doctrine §10 pour la table de renvoi vers ADR-025 → ADR-029 (à produire en L2-L6 après validation L1).
