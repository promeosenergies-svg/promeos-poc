# Patch securite conformite BACS + OPERAT

> Date : 2026-03-16
> Commit : `fc6de2d`
> Objectif : Supprimer tout faux sentiment de conformite

---

## Fichiers modifies

| Fichier | Zone | Changement |
|---------|------|-----------|
| `domain/compliance/complianceLabels.fr.js` | Labels | +4 statuts, +5 warnings, +4 labels declaration |
| `components/ExportOperatModal.jsx` | OPERAT | Banner simulation, titre, bouton renommes |
| `pages/tertiaire/TertiaireEfaDetailPage.jsx` | OPERAT | Banner aide conformite, section renommee |
| `routes/operat.py` | Backend | Flag simulation, headers disclaimer, filename |
| `__tests__/compliance_safety.test.js` | Tests front | 12 tests garde-fous |
| `tests/test_operat_safety.py` | Tests back | 4 tests garde-fous |

---

## Diff logique par zone

### OPERAT

| Avant | Apres |
|-------|-------|
| Titre : "Export OPERAT (CSV)" | "Preparation dossier OPERAT (CSV)" |
| Pas de banner warning | Banner orange "Simulation — aucun depot reel" |
| "Telecharger CSV" | "Telecharger le pack preparatoire" |
| "Exporter le pack" | "Generer le pack preparatoire" |
| "Actions OPERAT" | "Preparation dossier OPERAT" |
| Pas de mention operat.ademe.fr | Mention explicite du depot sur operat.ademe.fr |
| Filename : `OPERAT_export_{org}_{year}.csv` | `OPERAT_PREPARATOIRE_{org}_{year}.csv` |
| Pas de flag simulation dans l'API | `is_real_submission: false` + headers disclaimer |

### BACS / Statuts

| Avant | Apres |
|-------|-------|
| Statuts : conforme, non_conforme, a_risque, a_qualifier, derogation, hors_perimetre | + evaluation_incomplete, preparation_en_cours, classe_a_verifier, preuves_non_tracables |
| Pas de warnings securite | 5 CONFORMITE_WARNINGS (simulation, baseline, trajectoire, preuves, classe GTB) |
| DeclarationStatus "exported" sans label FR | "Pack preparatoire genere" |
| DeclarationStatus "submitted_simulated" sans label FR | "Simulation non deposee" |

### Labels

| Avant | Apres |
|-------|-------|
| Pas de CONFORMITE_WARNINGS | 5 avertissements centralises |
| Pas de DECLARATION_STATUS_LABELS | 4 labels FR explicites |

---

## Formulations supprimees

| Formulation supprimee | Remplacement |
|----------------------|-------------|
| "Export OPERAT" (titre modal) | "Preparation dossier OPERAT" |
| "Exporter le pack" (bouton EFA) | "Generer le pack preparatoire" |
| "Telecharger CSV" (bouton modal) | "Telecharger le pack preparatoire" |
| "Pre-verification et export du dossier declaratif" (sous-titre) | "Pre-verification et generation du pack preparatoire" |
| "Actions OPERAT" (titre section) | "Preparation dossier OPERAT" |

---

## Nouveaux garde-fous

| Garde-fou | Type | Fichier |
|-----------|------|---------|
| Banner "Simulation — aucun depot reel" | UI | ExportOperatModal.jsx |
| Banner "Aide a la conformite" + operat.ademe.fr | UI | TertiaireEfaDetailPage.jsx |
| `is_real_submission: false` dans response preview | API | operat.py |
| `X-PROMEOS-Submission-Type: simulation_preparatoire` | HTTP header | operat.py |
| `X-PROMEOS-Disclaimer` | HTTP header | operat.py |
| Filename `PREPARATOIRE` | Fichier | operat.py |
| Statut `evaluation_incomplete` | Label | complianceLabels.fr.js |
| Statut `classe_a_verifier` | Label | complianceLabels.fr.js |
| Statut `preuves_non_tracables` | Label | complianceLabels.fr.js |
| Warning `operat_simulation` | Label | complianceLabels.fr.js |
| Warning `baseline_absente` | Label | complianceLabels.fr.js |
| Warning `trajectoire_non_validee` | Label | complianceLabels.fr.js |
| Warning `classe_gtb_inconnue` | Label | complianceLabels.fr.js |

---

## Tests

| Suite | Tests | Resultat |
|-------|-------|----------|
| Frontend compliance_safety | 12 | Passe |
| Backend test_operat_safety | 4 | Passe |
| Build Vite | - | Passe |

---

## Risques restants apres patch

| Risque | Severite | Pourquoi |
|--------|----------|----------|
| Les nouveaux statuts (evaluation_incomplete, classe_a_verifier) ne sont pas encore **consommes** par les composants UI existants | Moyenne | Les labels existent mais les composants affichent toujours les anciens statuts — a brancher dans un sprint dedie |
| Le score BACS peut encore afficher "conforme" sans verification classe A/B | Moyenne | Le backend ne bloque pas encore — necessite patch compliance_rules.py |
| La trajectoire OPERAT n'est toujours pas calculee | Haute | Necessite le modele consommation EFA (Sprint conformite 1) |
| L'audit-trail preuves n'existe toujours pas | Haute | Necessite ProofEventLog (Sprint conformite 2) |

---

## Ce qui est securise maintenant

1. Un utilisateur voit clairement que l'export OPERAT est une **simulation**
2. Le mot "depot" n'apparait jamais sans "aucun" ou "a confirmer"
3. Le fichier telecharge s'appelle `PREPARATOIRE` (pas `export`)
4. L'API retourne `is_real_submission: false` dans chaque preview
5. Les labels de declaration ne disent jamais "soumis" ou "depose"
6. 16 tests automatises verifient ces garde-fous
