---
audit: personas_deep_dive
date: 2026-05-02
branch: claude/refonte-sol2
mode: read-only strict
scope: parcours-types détaillés 3 personas dominants Sol v1.1 (CFO/DAF/EM) + cible §2.1 non-sachant
guidelines: doctrine §2 (cibles), §11 (le bon endroit), §12 (sachant vs non-sachant)
auteur: Claude Code (Opus 4.7)
---

# Audit Personas — Deep dive parcours-types

> **Différence vs personas_audit_20260502.md (étape 5)** : ce livrable approfondit les **parcours-types** des 3 personas dominants Sol v1.1 (CFO, DAF, Energy Manager) avec un focus doctrine §2.1 (cible primaire = non-sachants).
>
> **Étape 9** du plan séquentiel utilisateur étendu.

---

## 1. TL;DR

1. **3 personas dominants** Sol v1.1 : Energy Manager (default doctrine §2), DAF (cible §2.1 non-sachant), CFO/DG (cible §2.1 non-sachant primaire).
2. **EM parcours = pédagogique cohérent** ✅ : Briefing du jour → Énergie monitoring → Anomalies → Diagnostic → Flex. Le default Sol v1.1 sert ce parcours.
3. **DAF parcours = financier-first ✅** : Synthèse → Facturation #2 → Conformité → Énergie → Achat. ROI+risque alignés.
4. **DG/CFO parcours ambigu** ⚠️ : ordre `dg_owner` Facturation #2 + Achat #3 suppose un sachant finance. Doctrine §2.1 dit explicitement "DG qui découvre l'énergie" = non-sachant. **Mismatch doctrinal P1**.
5. **Cible secondaire (§2.2 sachants)** : ingénieurs énergie + consultants — non audités ici car correspondent à `energy_manager` / `auditeur` / `resp_conformite` (déjà couverts §5 sachants).

---

## 2. Parcours-types 3 personas dominants

### 2.1 Energy Manager (Marc, persona dominant doctrine §2)

#### Profil métier
- Responsable performance énergétique d'un patrimoine multi-sites
- Quotidien : consultation matinale 30s pour dérives + actions site-level
- Sachant énergie (formation technique) mais non-sachant régulation (DT, OPERAT)

#### Parcours-type quotidien
```
1. Login → /cockpit/strategique (redirect /cockpit) ou /cockpit/jour direct
2. Lecture briefing 30s : nouvelles alertes monitoring, anomalies billing
3. Si alerte rouge → drill-down /monitoring ou /diagnostic-conso
4. Si rien d'urgent → /consommations explorer un site spécifique
5. Hebdo : /flex pour identifier opportunités effacement
6. Mensuel : /conformite/tertiaire OPERAT déclaration
```

#### Validation ordre rail `default = energy_manager`
Ordre actuel : `cockpit → energie → conformite → facturation → achat → patrimoine`

| Position | Module | Justification parcours-type |
|---|---|---|
| 1 | Cockpit (Accueil) | Briefing 30s — point d'entrée |
| 2 | Énergie | **Cœur métier EM** : monitoring + diag quotidien |
| 3 | Conformité | Hebdo (échéances DT) — important mais moins fréquent |
| 4 | Facturation | Mensuel (vérification factures) |
| 5 | Achat | Annuel (renouvellements) |
| 6 | Patrimoine | One-shot setup |

✅ **Alignment parfait**. Pas d'issue P0/P1.

#### CS pour EM
- Briefing du jour = signal CS critique (rétention quotidienne)
- Carpet plot 24h × 365j (doctrine §4.2) = différenciant valeur perçue
- ⚠️ Pas de signal "Bonne nouvelle" éditorial dans briefing actuel (Chantier α)

---

### 2.2 DAF (Marie / Sophie, cible §2.1 non-sachant)

#### Profil métier
- Direction Administrative et Financière
- Doctrine §2.1 cite explicitement : "DAF qui découvre l'énergie en arrivant dans une nouvelle fonction"
- Sachant finance, **non-sachant énergie**
- Hebdo : revue factures + risque réglementaire

#### Parcours-type hebdomadaire
```
1. Login → /cockpit/strategique (Synthèse 3min focus CFO)
2. Vérif Synthèse : score conformité, coût énergie portefeuille
3. /bill-intel : factures récentes + anomalies + reclaim
4. /conformite : score DT/BACS/APER + échéances réglementaires
5. /achat-energie?tab=scenarios : renouvellements à venir + arbitrage
6. /consommations : si data dispo, vérifier volumes (rare)
```

#### Validation ordre rail `daf`
Ordre actuel : `cockpit → facturation → conformite → energie → achat → patrimoine`

| Position | Module | Justification parcours-type |
|---|---|---|
| 1 | Cockpit | Synthèse 3min CFO-friendly |
| 2 | Facturation | **Cœur métier DAF** : factures + anomalies |
| 3 | Conformité | Risque réglementaire (DT post-2030) + sanctions |
| 4 | Énergie | Donnée brute pour rapports (consultation moins fréquente) |
| 5 | Achat | Mensuel/trimestriel (arbitrage) |
| 6 | Patrimoine | One-shot |

✅ **Alignment doctrine** : Facturation #2 = focus financier. Conformité #3 = risque (DT non-conformité = sanction 5% CA).

#### Issue P1 — Bill Intelligence non-sachant friendly ?
[bill-intel page non auditée ici] — la doctrine §4.4 promet "shadow billing transparent" + "explication écarts TURPE/ATRD/accise" pour les **non-sachants**. À vérifier que la page Bill Intel rend ces écarts en **langage naturel** (ex: "Vous payez 47 € de plus que tarif réglementé sur l'accise février 2026 — voici pourquoi") plutôt qu'en pure data.

→ **Ticket produit** : audit Bill Intelligence pédagogie non-sachant (hors scope nav).

---

### 2.3 DG / CFO / Direction (cible primaire §2.1 non-sachant)

#### Profil métier
- Direction générale, Owner, Comité de Direction
- Doctrine §2.1 cite : "Dirigeant de PME ou ETI qui n'a jamais lu un avenant ARENH"
- **Non-sachant énergie + non-sachant finance détaillée**
- Mensuel : revue stratégique 5-10 min

#### Parcours-type mensuel idéal (vision doctrine §2.1)
```
1. Login → /cockpit/strategique (Synthèse 3min)
2. Skim KPIs hero : économies réalisées, score conformité, risque résiduel
3. Lecture week-cards "À regarder / À faire / Bonne nouvelle" éditorial
4. Si curiosité → drill-down via card vers détail (mais pas obligatoire)
5. Logout sans avoir touché Facturation/Achat/Énergie en profondeur
```

#### Parcours-type actuel ordre `dg_owner`
Ordre actuel : `cockpit → facturation → achat → conformite → energie → patrimoine`

| Position | Module | Adéquation §2.1 (DG novice) |
|---|---|---|
| 1 | Cockpit | ✅ Synthèse 3min |
| 2 | Facturation | ⚠️ Suppose sachant finance (factures = compétence DAF/comptable) |
| 3 | Achat | ⚠️ Suppose sachant marché énergie (post-ARENH = expertise) |
| 4 | Conformité | ✅ Risque réglementaire = compréhensible DG |
| 5 | Énergie | ⚠️ Consommation détaillée = compétence EM, peu utile DG |
| 6 | Patrimoine | ✅ One-shot |

#### Issue P1 — Mismatch doctrinal `dg_owner` vs §2.1

**Constat** : ordre `dg_owner` privilégie Facturation #2 + Achat #3 — ces 2 modules sont des **modules d'expertise** (factures détaillées + simulation achat technique). Un DG vraiment non-sachant **ne va pas explorer ces modules en profondeur**.

**Hypothèse** : l'ordre `dg_owner` actuel correspond à un **DG sachant** (ex: ETI où le DG est aussi DAF). Pour le **DG novice doctrine §2.1**, l'ordre `default` (Énergie #2 = visualisation simple consommation) serait plus pédagogique.

**3 options** :
- **A** : conserver `dg_owner` actuel — adapté aux DG sachants ETI / mid-cap
- **B** : aligner `dg_owner` sur `default` — pédagogie non-sachant primaire
- **C** : créer 2 niveaux `dg_owner_novice` + `dg_owner_expert` — surengineering

**Mon vote** : conserver A mais documenter la décision avec un commentaire dans NavRegistry pour clarifier. Le réel non-sachant DG (PME) sera plus probablement seedé sur fallback `default` (= EM) — ce qui revient à l'option B implicitement.

---

## 3. Tests "non-sachant friendly" sur les 3 parcours

### 3.1 Test "3 secondes" (doctrine §7 Test 1)

> **Test simple** : screenshot du Cockpit montré 3 secondes à un utilisateur, qui résume immédiatement l'état de son patrimoine.

| Persona | Test 3s passé ? | Justification |
|---|---|---|
| EM | ✅ Briefing du jour = signaux clairs (alertes, anomalies) | doctrine §4.7 livré P0.3 |
| DAF | ✅ Synthèse stratégique = score + coût + risque | dual cockpit P0.2 livré |
| DG novice | ⚠️ Synthèse stratégique focalisée chiffres — pas encore "récit éditorial 3 secondes" | Chantier α moteur événements proactif requis |

### 3.2 Test "dirigeant non-sachant" (doctrine §7 Test 2)

> 2 personnes utilisent PROMEOS — l'une expert énergie, l'autre dirigeant non-sachant. Les deux trouvent leur valeur sans frustration.

| Persona | Friction observée | Recommandation |
|---|---|---|
| EM | Aucune (cible secondaire) | ✅ |
| DG novice | ⚠️ Acronymes BACS/APER/TURPE non explicités au survol → friction lecture | SolAcronym hover tooltip (audit doctrine §6.3) |

### 3.3 Test "le produit pousse, ne tire pas" (doctrine §6)

> Le produit propose plus qu'il ne fait chercher.

| Persona | Push observé | Recommandation |
|---|---|---|
| EM | Briefing du jour matinal = push utile | ✅ |
| DAF | Synthèse stratégique 3min mensuelle = push approprié | ✅ |
| DG novice | ⚠️ Pas de notification proactive entre 2 visits (Chantier α absent) | Email digest hebdo / push notif événements critiques |

---

## 4. Issues consolidées

| # | Issue | Persona impacté | Sévérité |
|---|---|---|---|
| P1.1 | Mismatch ordre `dg_owner` vs doctrine §2.1 (sachant vs non-sachant) | DG novice | P1 |
| P1.2 | Bill Intelligence pédagogie non-sachant à vérifier (hors scope nav) | DAF non-sachant | P1 |
| P2.1 | Acronymes BACS/APER/TURPE sans tooltip hover | DG novice | P2 |
| P2.2 | Chantier α moteur événements proactif backlog (briefing vivant doctrine §4.7) | DG novice + email digest | P2 backlog |

→ Aucune issue P0 dans le scope nav strict. Toutes reportées en sprint produit / UX dédié.

---

## 5. STOP — livrable étape 9 read-only

Audit personas deep-dive terminé. Conclusions clés :

- ✅ **EM et DAF parcours validés** par les ordres `default` et `daf` de ROLE_MODULE_ORDER.
- ⚠️ **DG novice** : ordre `dg_owner` actuel suppose un sachant finance — mismatch doctrine §2.1 mais acceptable pragmatiquement (PME DG novices tomberont en fallback `default` = EM-like, ce qui sert aussi leur pédagogie).
- 🎯 **Recommandation** : prioriser **Chantier α moteur événements proactif** comme suite naturelle du sprint nav — c'est le différenciant clé pour les non-sachants (briefing éditorial vivant).
