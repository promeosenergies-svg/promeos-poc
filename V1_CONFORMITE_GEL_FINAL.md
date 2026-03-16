# PROMEOS V1 Conformite — Pack de cloture

> Date : 2026-03-16
> Perimetre : OPERAT + BACS + Integrite patrimoine → conformite
> Bilan : 20 commits, 173 tests, 0 regression
> Statut : **GEL V1 DU PERIMETRE COEUR — limites connues acceptees**

---

# 1. EXECUTIVE SUMMARY

PROMEOS V1 Conformite est un **outil d'aide a la preparation de la conformite reglementaire** pour les batiments tertiaires en France (Decret Tertiaire / OPERAT et BACS / Decret n°2020-887).

**Ce que V1 fait :**
- Calcule et suit la trajectoire energetique -40%/-50%/-60%
- Evalue les 10 exigences fonctionnelles BACS R.175-3
- Trace chaque donnee, source, calcul et export
- Genere des packs preparatoires OPERAT certifies (SHA-256)
- Detecte les blockers et propose des remediations actionnables
- Maintient la coherence patrimoine ↔ conformite

**Ce que V1 ne fait PAS :**
- Ne certifie JAMAIS la conformite
- Ne depose PAS sur la plateforme OPERAT reelle
- Ne remplace PAS un audit reglementaire
- Ne garantit PAS la fiabilite des donnees saisies manuellement

**Formulation de reference :**
> PROMEOS prepare le dossier de conformite. Le depot reglementaire et la validation restent de la responsabilite de l'assujetti.

---

# 2. MATRICE DE GEL V1

| Zone | Statut | Justification |
|------|--------|---------------|
| **OPERAT trajectoire (-40/-50/-60)** | GELE V1 | Service + 16 tests + validation API |
| **OPERAT audit-trail** | GELE V1 | ComplianceEventLog + journalisation create/update/compute |
| **OPERAT export manifest** | GELE V1 | SHA-256 + metadata + retention 5 ans |
| **OPERAT normalisation DJU** | ACCEPTE V1 MAIS LIMITE | Table RT2012 interne, pas d'API Meteo-France externe |
| **OPERAT gouvernance statut** | GELE V1 | 4 modes (raw/normalized/mixed/review), prudent par defaut |
| **OPERAT source trust** | GELE V1 | Weather provider + actor resolver + baseline policy |
| **OPERAT UI trajectoire** | GELE V1 | Bloc EFA detail + brute vs normalisee + badges |
| **OPERAT wording securite** | GELE V1 | "Simulation", "pack preparatoire", jamais "depot" |
| **BACS compliance gate** | GELE V1 | 5 statuts prudents + jamais compliant |
| **BACS regulatory engine** | GELE V1 | 6 axes (eligibilite, R.175-3, exploitation, inspection, preuves, statut) |
| **BACS remediation workflow** | GELE V1 | Action → preuve → revue, jamais auto-leve |
| **BACS panel UI** | GELE V1 | Branche dans Site360 > Conformite |
| **BACS alertes** | GELE V1 | Inspection, preuve, formation, action overdue |
| **BACS ready_for_external_review** | GELE V1 | Uniquement si 0 blocker + 0 alerte |
| **Integrite cascade archivage** | GELE V1 | Site archive → EFA + BACS archives |
| **Integrite surface sync** | GELE V1 | EfaBuilding synchro auto |
| **Integrite recalcul CVC** | GELE V1 | Auto-recompute sur add/update/delete |
| **Integrite reevaluation usage** | GELE V1 | review_required si type/NAF change |
| **Integrite job coherence** | GELE V1 | Orphelins + desync + BACS stale |
| **Badge UI desynchronise** | POST-V1 | Pas encore visible dans le front |
| **Auto-provision EFA/BACS** | POST-V1 | Creation manuelle uniquement |
| **Upload fichier preuve** | POST-V1 | Reference texte, pas de stockage fichier |
| **Notifications email** | POST-V1 | Structure prete, envoi pas active |
| **IAM actor complet** | ACCEPTE V1 MAIS LIMITE | resolve_actor fonctionne, auth souvent absente |
| **Source meteo externe** | ACCEPTE V1 MAIS LIMITE | Table RT2012 = verified interne, pas d'API externe |
| **Signature numerique export** | POST-V1 | Checksum SHA-256 present, pas de X.509 |
| **Depot reel OPERAT** | POST-V1 | Simulation par design |

---

# 3. POSITIONNEMENT PRODUIT RECOMMANDE

## Presentation commerciale prudente
> PROMEOS centralise et structure la preparation a la conformite reglementaire pour les batiments tertiaires (Decret Tertiaire, BACS). Il calcule la trajectoire energetique, identifie les ecarts, trace les preuves et genere les dossiers preparatoires pour faciliter les revues internes et la preparation aux declarations reglementaires.

## Presentation demo
> PROMEOS aide les gestionnaires de patrimoine tertiaire a piloter leur preparation reglementaire : trajectoire OPERAT, evaluation BACS, gestion des preuves et des actions correctives. Chaque donnee est tracee, chaque statut est prudent, chaque export est certifie par un checksum.

## Presentation audit interne
> PROMEOS V1 couvre la preparation a la conformite Decret Tertiaire et BACS avec un moteur de trajectoire (-40/-50/-60%), un moteur reglementaire BACS (10 exigences R.175-3), un audit-trail complet, des exports certifies SHA-256, et un workflow de remediation action → preuve → revue. Le systeme ne certifie jamais la conformite et utilise des statuts prudents (review_required, not_evaluable).

## Wording INTERDIT

| Interdit | Pourquoi | Alternative |
|----------|----------|-------------|
| "PROMEOS certifie conforme" | Faux — PROMEOS n'est pas un organisme de certification | "PROMEOS aide a preparer la conformite" |
| "Depot OPERAT effectue" | Faux — aucun depot reel | "Pack preparatoire genere" |
| "Site conforme BACS" | Jamais demontrable par PROMEOS seul | "Pret pour revue interne" |
| "Donnees verifiees" | Sauf si source = API Meteo-France ou import factures | "Donnees tracees avec qualification de source" |
| "Risque zero" | Impossible a garantir | "Aucune non-conformite bloquante identifiee dans le perimetre analyse" |
| "Score de conformite" sans contexte | Trop affirmatif | "Score de preparation (aide a la conformite)" |

---

# 4. CHECKLIST DE GEL V1

## Avant demo

- [ ] Seed Helios fonctionne (`python -m services.demo_seed --pack helios --size S --reset`)
- [ ] Quick-create site fonctionne (nom + adresse + usage)
- [ ] Drawer completude affiche les 5 actions
- [ ] EFA creee via wizard tertiaire
- [ ] Trajectoire OPERAT affichee dans EFA detail
- [ ] Export OPERAT preparatoire genere avec checksum
- [ ] Banner "Aide a la conformite" visible partout
- [ ] BACS panel affiche dans Site360 > Conformite
- [ ] Action corrective creee depuis blocker
- [ ] Build frontend sans erreur

## Avant livraison interne

- [ ] 173 tests backend passent
- [ ] Tests front (step32, patrimoineV58, compliance_safety) passent
- [ ] Endpoint /coherence retourne "clean" sur seed propre
- [ ] Endpoint /orphans retourne 0 orphelin
- [ ] Archive site → EFA + BACS cascades
- [ ] Modif CVC → BACS recalcule
- [ ] Modif usage → review_required

## Avant communication externe

- [ ] Aucun wording interdit dans l'UI
- [ ] "Simulation" visible sur tout export
- [ ] is_compliant_claim_allowed = false PARTOUT
- [ ] Tous les labels FR dans complianceLabels.fr.js sont prudents
- [ ] README/CHANGELOG mis a jour

---

# 5. SMOKE TESTS FINAUX

| # | Scenario | Action | Resultat attendu |
|---|----------|--------|-----------------|
| 1 | Site cree | Quick-create "Bureau Test" | Site visible, completude 50% |
| 2 | Site archive | Archive site via API | EFA + BACS cascades, non visibles |
| 3 | Surface modifiee | PATCH surface 2000 | EfaBuilding synchro |
| 4 | Usage modifie | PATCH type "entrepot" | EFA + BACS → review_required |
| 5 | CVC modifie | PUT /system/{id} | BACS recalcule auto |
| 6 | Export OPERAT | POST /operat/export | CSV + manifest + checksum |
| 7 | Trajectoire | GET /targets/validate | Baseline + current + status |
| 8 | BACS blocker | GET /regulatory-assessment | Blockers + remediation |
| 9 | Action corrective | POST /remediation | Action creee, status open |
| 10 | Preuve rattachee | POST /attach-proof | Status → ready_for_review |
| 11 | Revue preuve | POST /review-proof accepted | Status → closed |
| 12 | Coherence propre | GET /coherence | status = clean |
| 13 | Orphelin simule | Entite conformite orpheline simulee | Detectee par /coherence |

---

# 6. BACKLOG POST-V1 PRIORISE (ICE)

| # | Sujet | Impact | Confiance | Facilite | ICE | Business | Reglementaire |
|---|-------|--------|-----------|----------|-----|----------|---------------|
| 1 | Badge UI desynchronise | 8 | 9 | 8 | 576 | Visibilite utilisateur | Transparence |
| 2 | Auto-provision EFA/BACS a creation site | 9 | 7 | 5 | 315 | Onboarding rapide | Couverture auto |
| 3 | Upload fichier preuve | 8 | 8 | 5 | 320 | Preuve reelle | Audit-trail |
| 4 | Source meteo externe (API) | 7 | 6 | 4 | 168 | Fiabilite | Normalisation |
| 5 | Notifications email echeances | 7 | 8 | 5 | 280 | Pilotage | Echeances |
| 6 | Actor IAM complet | 6 | 7 | 5 | 210 | Tracabilite | Audit |
| 7 | Approbation inspection workflow | 6 | 7 | 4 | 168 | Qualite | Preuve |
| 8 | Signature numerique export | 5 | 6 | 3 | 90 | Certification | Juridique |
| 9 | Vue portefeuille coherence | 7 | 7 | 4 | 196 | Pilotage multi-site | Visibilite |
| 10 | Depot reel OPERAT (API ADEME) | 5 | 3 | 2 | 30 | Valeur ajoutee | Integration |

---

# 7. TOP 5 ACTIONS IMMEDIATES

| # | Action | Effort | Owner | Impact |
|---|--------|--------|-------|--------|
| 1 | **Smoke test complet** (13 scenarios) avant freeze | S | QA | Validation avant gel |
| 2 | **Badge UI "a recalculer / desynchronise"** dans Site360 | S | Frontend | Visibilite utilisateur |
| 3 | **Upload preuve fichier** (stockage local ou S3 minimal) | M | Full stack | Preuve reelle |
| 4 | **Vue portefeuille coherence** (dashboard multi-site) | M | Full stack | Pilotage |
| 5 | **Release GitHub V1 Conformite** avec tag + notes | S | Release | Communication |

---

# 8. BILAN CHIFFRE

| Metrique | Valeur |
|----------|--------|
| Commits conformite | 20 |
| Tests backend | 173 |
| Tests frontend securite | 12 |
| Modeles crees | 7 (EfaConsumption, ComplianceEventLog, ExportManifest, FunctionalReq, ExploitationStatus, ProofDoc, RemediationAction) |
| Services crees | 7 (trajectory, normalization, weather, actor, alerts, regulatory engine, sync) |
| Endpoints crees | 15+ |
| Composants UI | 2 (BacsRegulatoryPanel, EfaTrajectoryBlock + EfaExportHistory) |
| Statuts prudents | is_compliant_claim_allowed = false TOUJOURS |
