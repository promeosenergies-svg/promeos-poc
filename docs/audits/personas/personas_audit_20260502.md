---
audit: personas_navigation
date: 2026-05-02
branch: claude/refonte-sol2
mode: read-only strict
scope: 11 UserRole vs 8 ROLE_MODULE_ORDER + parcours-types nav
doctrine_ref: docs/vision/promeos_sol_doctrine.md (§2 cibles, §11 le bon endroit)
auteur: Claude Code (Opus 4.7)
---

# Audit Personas — Couverture Navigation

> **But** : valider que chacun des 11 UserRole PROMEOS a un parcours nav cohérent avec sa fonction et la doctrine §2 (non-sachants prioritaires).
>
> **Périmètre** : `ROLE_MODULE_ORDER` (NavRegistry.js:981-995), `ROLE_LABELS` (AppShell.jsx:40-52), `UserRole` enum (backend/models/enums.py).

---

## 1. TL;DR

1. **Couverture incomplète** : 11 `UserRole` définis backend, **seulement 8 ont un ordre rail dédié**. 3 rôles (DSI_ADMIN, PRESTATAIRE, AUDITEUR, PMO_ACC) → fallback `default` (= ENERGY_MANAGER) — comportement potentiellement incohérent avec leur fonction métier réelle.
2. **Persona dominant Sol §2 = ENERGY_MANAGER** ✅ aligné `default` (Phase 1.E P0.5 + Phase 3.E P1.8 reseed). Cohérence doctrine respectée.
3. **Persona DG/CFO non-sachant** (doctrine §2.1 cible primaire) → ordre `dg_owner` privilégie Facturation #2 + Achat #3 (focus financier) — **bon alignment** mais conformité réglementaire reléguée #4 alors que doctrine §2.1 cite explicitement "DG qui découvre l'énergie".
4. **3 personas sans ordre dédié** (DSI_ADMIN, PRESTATAIRE, AUDITEUR, PMO_ACC) ont des fonctions très différentes du Energy Manager → **trou couverture P1**. Ex : un AUDITEUR cherche d'abord Conformité + tracabilité ; un PRESTATAIRE cherche Patrimoine + Contrats.
5. **Aucun test ne valide les 11 personas** — les 9 tests parité Phase 3.D ne couvrent que les 8 personas qui ont un ordre dédié. Si une dérive silencieuse fait disparaître un persona de ROLE_MODULE_ORDER, le test cross-cutting ne détecte pas (il itère sur la liste statique).

---

## 2. Inventaire — 11 UserRole vs 8 ROLE_MODULE_ORDER

| # | UserRole enum | ROLE_LABELS UI | ROLE_MODULE_ORDER | Couverture |
|---|---|---|---|---|
| 1 | `DG_OWNER` | DG / Propriétaire | ✅ dédié | OK |
| 2 | `DSI_ADMIN` | DSI / Admin | ❌ fallback default | **TROU** |
| 3 | `DAF` | DAF | ✅ dédié | OK |
| 4 | `ACHETEUR` | Acheteur | ✅ dédié | OK |
| 5 | `RESP_CONFORMITE` | Resp. Conformité | ✅ dédié | OK |
| 6 | `ENERGY_MANAGER` | Responsable Énergie | ✅ dédié (= default) | OK |
| 7 | `RESP_IMMOBILIER` | Resp. Immobilier | ✅ dédié | OK |
| 8 | `RESP_SITE` | Resp. Site | ✅ dédié | OK |
| 9 | `PRESTATAIRE` | Prestataire | ❌ fallback default | **TROU** |
| 10 | `AUDITEUR` | Auditeur | ❌ fallback default | **TROU** |
| 11 | `PMO_ACC` | PMO / Acc. | ❌ fallback default | **TROU** |

→ **8/11 personas couverts (73 %)**. 4 personas tombent en fallback (DSI_ADMIN traité dans le bilan car distinct).

---

## 3. Analyse persona × parcours-type × doctrine

### 3.1 ENERGY_MANAGER (default + persona dominant Sol §2)

| Aspect | Valeur |
|---|---|
| Ordre rail | `cockpit → energie → conformite → facturation → achat → patrimoine` |
| Fonction métier | Pilote la performance énergétique du patrimoine quotidiennement |
| Doctrine §2 | Persona dominant — cible Sol v1.1 |
| Parcours type | Briefing du jour → consommations + monitoring → diagnostic anomalies → flex |

**✅ Alignment** : Énergie #2 immédiatement après Accueil. Conformité #3 (échéances DT/BACS proches). Facturation #4 (suivi mensuel). Patrimoine relégué (one-shot setup).

### 3.2 DG_OWNER (compte démo principal post P1.8 = ENERGY_MANAGER)

| Aspect | Valeur |
|---|---|
| Ordre rail | `cockpit → facturation → achat → conformite → energie → patrimoine` |
| Fonction métier | Décisionnel financier + stratégique |
| Doctrine §2.1 | Cible primaire non-sachant — "Dirigeant PME/ETI qui n'a jamais lu un avenant ARENH" |
| Parcours type | Synthèse stratégique → factures coût → arbitrage achat → conformité (if pressing) |

**⚠️ Issue P1 detected** : Doctrine §2.1 affirme que les DG sont des **non-sachants** qui veulent un parcours guidé. Mais l'ordre rail `dg_owner` suppose un usage "expert" (Facturation #2 = expertise comptable). Pour un DG vraiment non-sachant qui découvre, l'ordre `default` (Énergie #2 = consommation visuelle simple) serait plus pédagogique.

→ **Question UX** : faut-il deux niveaux de DG : "DG novice" (= default) et "DG sachant" (= ordre actuel) ? Hors scope mais à tracker.

### 3.3 DAF

| Aspect | Valeur |
|---|---|
| Ordre rail | `cockpit → facturation → conformite → energie → achat → patrimoine` |
| Fonction métier | Finance + risque + compliance |
| Parcours type | Synthèse → factures + anomalies → conformité réglementaire → coût énergie |

**✅ Alignment** : Facturation #2 (priorité métier finance), Conformité #3 (risque réglementaire), Énergie #4 (donnée brute), Achat #5, Patrimoine last. Cohérent.

### 3.4 ACHETEUR

| Aspect | Valeur |
|---|---|
| Ordre rail | `cockpit → achat → facturation → energie → conformite → patrimoine` |
| Fonction métier | Stratégie d'achat énergie |
| Parcours type | Échéances → scénarios d'achat → factures (verification) → consos (volume) |

**✅ Alignment** : Achat #2 dominant, Facturation #3 (référence prix), Énergie #4 (volumes), Conformité reléguée. Cohérent.

### 3.5 RESP_CONFORMITE

| Aspect | Valeur |
|---|---|
| Ordre rail | `cockpit → conformite → energie → facturation → achat → patrimoine` |
| Fonction métier | Audit réglementaire + reporting CSRD/DT/OPERAT |
| Parcours type | Score conformité → tertiaire/OPERAT → APER → vérif consos |

**✅ Alignment** : Conformité #2 dominant. Énergie #3 (donnée pour rapports). Cohérent.

### 3.6 RESP_IMMOBILIER

| Aspect | Valeur |
|---|---|
| Ordre rail | `cockpit → conformite → energie → facturation → achat → patrimoine` (= resp_conformite) |
| Fonction métier | Asset management bâtiments |
| Parcours type | Sites + bâtiments + surfaces → conformité DT par bâtiment → consos par site |

**⚠️ Issue P2 detected** : ordre identique à resp_conformite, alors que la fonction Resp. Immobilier devrait privilégier **Patrimoine** (registre sites/bâtiments). Mais Patrimoine est en dernier (groupBoundary 'config'). Conflit doctrinal.

→ Patrimoine en dernière position est une **règle inviolable** (P0.5 + tests parité Phase 3.D). Donc Resp. Immobilier reste contraint à un ordre similaire. Le panel Patrimoine reste accessible en 1 clic via le rail. Mineur.

### 3.7 RESP_SITE

| Aspect | Valeur |
|---|---|
| Ordre rail | `cockpit → energie → conformite → facturation → achat → patrimoine` (= default) |
| Fonction métier | Gestion d'un site spécifique (technicien terrain) |
| Parcours type | Briefing du jour → consos site → anomalies → diagnostic → flex |

**✅ Alignment** : ordre identique au default (énergie focus). Cohérent — un Resp. Site est essentiellement un Energy Manager focalisé site-level.

### 3.8 DSI_ADMIN, PRESTATAIRE, AUDITEUR, PMO_ACC (fallback default)

| Persona | Fonction métier | Ordre attendu intuitivement | Ordre actuel (fallback) | Issue |
|---|---|---|---|---|
| **DSI_ADMIN** | Administration plateforme + intégrations | Admin module first ? | Default (admin caché expertOnly) | ⚠️ P1 — mode expert non-default |
| **PRESTATAIRE** | Audit ponctuel par mandat client | Patrimoine + Conformité | Default (Énergie #2) | ⚠️ P1 — divergence usage |
| **AUDITEUR** | Vérification CSRD / Audit Énergie | Conformité dominant | Default (Énergie #2) | ❌ **P0** — Conformité #3, devrait être #2 |
| **PMO_ACC** | Pilotage projet ACC (Autoconsommation Collective) | Énergie + APER + Patrimoine | Default | ⚠️ P1 — APER/Flex pertinents mais pas mis en avant |

**Sévérité globale P0 sur AUDITEUR** : un auditeur réglementaire qui voit Énergie en #2 au lieu de Conformité subit une friction immédiate. Et les comptes auditeur seedés (Jean Dupont `j.dupont@helios-energie.fr` = AUDITEUR cf orchestrator.py) ont ce comportement.

---

## 4. Issues consolidées

### P0 — Critiques

| # | Issue | Impact |
|---|---|---|
| P0.1 | **AUDITEUR sans ordre dédié** — fallback default place Conformité #3 alors que c'est leur module dominant. Compte démo `j.dupont@helios-energie.fr` impacté. | UX persona auditeur biaisée |

### P1 — Important

| # | Issue | Impact |
|---|---|---|
| P1.1 | **DSI_ADMIN sans ordre dédié** — administrateur plateforme tombe sur ordre Energy Manager. Pas de clé d'entrée admin direct. | UX power user |
| P1.2 | **PRESTATAIRE / PMO_ACC** sans ordre dédié — fonctions très spécifiques (audit ponctuel mandat / pilotage ACC) servies par fallback générique. | UX persona spécialisé |
| P1.3 | **DG_OWNER ordre suppose sachant** — doctrine §2.1 affirme cible primaire = non-sachant DG. Risque mismatch pédagogique. | Doctrine alignment |

### P2 — Cosmétique

| # | Issue | Impact |
|---|---|---|
| P2.1 | **RESP_IMMOBILIER == RESP_CONFORMITE** ordre identique. Patrimoine pourrait être davantage signalé pour Resp. Immobilier (mais règle "Patrimoine last" inviolable). | Différenciation faible |
| P2.2 | **Tests parité 8 personas seulement** (Phase 3.D) — pas de garde-fou anti-régression sur les 3 fallback. Risque dérive silencieuse `ROLE_MODULE_ORDER` non détectée. | Couverture tests |

---

## 5. Recommandations actionables

### P0 — Fix immédiat possible

| # | Reco | Action |
|---|---|---|
| R0.1 | Ajouter ordre `auditeur` dans `ROLE_MODULE_ORDER` : `['cockpit', 'conformite', 'energie', 'facturation', 'achat', 'patrimoine']` (= resp_conformite). | NavRegistry.js +1 ligne |

### P1 — Sprint UX persona dédié

| # | Reco | Action |
|---|---|---|
| R1.1 | Ajouter `dsi_admin` : `['cockpit', 'conformite', 'energie', 'patrimoine', 'achat', 'facturation']` + flag isExpert auto-on (admin power user). | NavRegistry.js + AuthContext logic |
| R1.2 | Ajouter `prestataire` : `['cockpit', 'patrimoine', 'conformite', 'energie', 'facturation', 'achat']` (audit ponctuel mandat = focus patrimoine + conformité). | NavRegistry.js |
| R1.3 | Ajouter `pmo_acc` : `['cockpit', 'energie', 'conformite', 'achat', 'patrimoine', 'facturation']` (pilotage ACC = énergie + APER + achat ENR). | NavRegistry.js |
| R1.4 | Réviser doctrine §2.1 vs ordre `dg_owner` — DG novice ≠ DG sachant. Décision produit : 2 niveaux ou unifier. | Décision produit + doc |

### P2 — Tests + cosmétique

| # | Reco | Action |
|---|---|---|
| R2.1 | Étendre tests parité Phase 3.D à **11 personas** (les 4 fallback inclus, vérifier qu'ils retournent l'ordre default ou leur ordre dédié). | NavRegistry.test.js +4 tests |
| R2.2 | Tracker SG_NAV_FE_06 : "tout UserRole de UserRole enum DOIT exister dans ROLE_MODULE_ORDER OU être documenté comme fallback intentionnel". Source-guard backend + frontend. | nav_fe_source_guards.test.js + test backend |

---

## 6. Compatibilité doctrine §2 (non-sachants prioritaires)

| Persona | Sachant ou non-sachant ? (doctrine) | Ordre rail prend en compte ? |
|---|---|---|
| ENERGY_MANAGER | sachant (responsable énergie) | ✅ ordre expert |
| DG_OWNER | **non-sachant** (cible primaire §2.1) | ⚠️ ordre suppose sachant |
| DAF | non-sachant majoritaire (§2.1 "DAF qui découvre") | ✅ ordre Facturation #2 = pédagogique |
| ACHETEUR | sachant (achat = expertise) | ✅ ordre expert |
| RESP_CONFORMITE | sachant | ✅ ordre expert |
| RESP_IMMOBILIER | mixte | ⚠️ ordre identique resp_conformite |
| RESP_SITE | non-sachant majoritaire (§2.1 "opérateur de site en début de fonction") | ✅ ordre default = pédagogique |
| AUDITEUR | sachant | ❌ pas d'ordre dédié |
| PRESTATAIRE | sachant variable | ❌ pas d'ordre dédié |
| DSI_ADMIN | sachant tech | ❌ pas d'ordre dédié |
| PMO_ACC | sachant ACC | ❌ pas d'ordre dédié |

→ **Doctrine globalement respectée** mais 4 angles morts (P0.1 + P1.1-3) à combler.

---

## 7. STOP — livrable étape 5a read-only

Audit personas terminé read-only. **2 fixes P0 actionables** + **3 P1** + **2 P2** identifiés.

→ Phase 5b suivante : fix P0.1 (ordre auditeur) + R2.1 (tests étendus 11 personas) + SG_NAV_FE_06 (garde-fou anti-trou couverture).

P1 reportés en sprint UX persona dédié (action produit, pas nav).
