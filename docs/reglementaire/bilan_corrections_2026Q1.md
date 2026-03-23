# Bilan Corrections Réglementaires — Q1 2026

**Agent** : SENTINEL-REG | **Date** : 2026-03-22 | **Statut** : TERMINÉ — 0 régressions

---

## Résumé exécutif

5 corrections critiques appliquées au moteur de billing PROMEOS pour aligner le POC avec la réalité réglementaire au 22 mars 2026. 155 tests billing passent (0 échecs). Le seul test en échec sur l'ensemble du backend (`test_action_close_rules_v49`) est pré-existant et hors périmètre.

---

## Actions réalisées

### Action 1 — TVA 20% uniforme post 01/08/2025

| Aspect | Détail |
|--------|--------|
| **Source** | LFI 2025 art. 20, bofip ACTU-2025-00057, directive UE |
| **Changement** | TVA 5,5% → 20% sur abonnement, CTA et TURPE fixe depuis 01/08/2025 |
| **Fichiers** | `catalog.py` (get_tva_rate_for avec résolution temporelle), `engine.py` (propagation at_date dans compute_turpe_breakdown + gaz) |
| **Logique** | Si `at_date >= 2025-08-01` et `tva_rate < 0.10` → retourne 0.20 (sauf TVA_NORMALE/TVA_REDUITE qui sont des constantes) |
| **Rétrocompatibilité** | Factures avant 01/08/2025 conservent le 5,5% sur composantes fixes |
| **Tests** | Nouveau test `test_gas_tva_split_pre_august_2025` + `test_gas_tva_split_post_august_2025` |

### Action 2 — Accise élec T2 février 2026 (26,58 €/MWh)

| Aspect | Détail |
|--------|--------|
| **Source** | Loi de finances 2026 |
| **Changement** | Ajout tranche T2 (250 MWh–1 GWh) au 01/02/2026 : 0,02658 €/kWh |
| **Fichiers** | `catalog.py` (entrée ACCISE_ELEC_T2_FEV2026 + résolution temporelle), `tarifs_reglementaires.yaml` |
| **Résolution temporelle** | T2 : jan 2025 → 0.02050 | fév-jul 2025 → 0.02569 | août 2025-jan 2026 → 0.02579 | fév 2026+ → 0.02658 |

### Action 3 — Mécanisme de capacité B2B

| Aspect | Détail |
|--------|--------|
| **Source** | Enchères RTE 06/03/2025, loi de finances 2025 |
| **Changement** | Nouvelle composante `capacite` dans le moteur élec |
| **Fichiers** | `catalog.py` (CAPACITE_ELEC + CAPACITE_ELEC_2025), `engine.py` (composante entre accise et abonnement) |
| **Calcul** | kwh_total × 0,00043 €/kWh (3,15 €/MW × coeff 1.2 / 8760h) — 2025 : 0 €/MW |
| **Résolution temporelle** | 2025 → 0 (prix nul) | 2026+ → 0,00043 |

### Action 4 — TDN gaz B2B (Terme de Débit Normalisé)

| Aspect | Détail |
|--------|--------|
| **Source** | GRDF sites.grdf.fr/web/terme-debit-normalise, CRE n°2025-161 |
| **Changement** | Nouvelle composante `tdn` dans le moteur gaz, activée si débit > 40 Nm³/h et date ≥ 01/07/2026 |
| **Fichiers** | `catalog.py` (TDN_GAZ), `engine.py` (paramètre debit_normalise_nm3h + composante TDN) |
| **Calcul** | 5,52 €/an/Nm³h × débit_normalisé × prorata |
| **Paramètre** | `debit_normalise_nm3h` ajouté à `build_invoice_reconstitution()` (optionnel, rétrocompatible) |

### Action 5 — Migration ARENH → VNU

| Aspect | Détail |
|--------|--------|
| **Source** | Loi souveraineté énergétique, art. L. 336-1 Code énergie |
| **Changement** | Mise à jour des références textuelles ARENH → post-ARENH/VNU dans les agents IA, routes, KB seed |
| **Fichiers** | `regops_explainer.py`, `exec_brief_agent.py`, `purchase.py`, `orchestrator.py`, `tarifs_reglementaires.yaml` |
| **VNU dans YAML** | Seuils (78/110 €/MWh), statut dormant, révision triennale CRE |
| **Note** | Aucune référence au prix ARENH 42 €/MWh dans le billing engine (il n'y en avait pas) |

---

## Fichiers modifiés

| Fichier | Type de modification |
|---------|---------------------|
| `backend/services/billing_engine/catalog.py` | +TVA temporelle, +accise T2 2026, +capacité, +TDN, version |
| `backend/services/billing_engine/engine.py` | +at_date TURPE, +TVA gaz, +capacité, +TDN, +debit_normalise_nm3h |
| `backend/config/tarifs_reglementaires.yaml` | +accise 2026, +VNU, +TVA supprimée note |
| `backend/ai_layer/agents/regops_explainer.py` | ARENH → post-ARENH/VNU |
| `backend/ai_layer/agents/exec_brief_agent.py` | ARENH → post-ARENH/VNU |
| `backend/routes/purchase.py` | Commentaire ARENH → VNU |
| `backend/services/demo_seed/orchestrator.py` | KB seed ARENH → VNU |
| `backend/tests/test_billing_engine.py` | Alignement tests TURPE 7 (HPH/HCH/HPB/HCB), valeurs, TVA |
| `backend/tests/test_shadow_billing_gas.py` | Tests TVA pré/post 01/08/2025 |
| `backend/tests/test_billing_invariants_p0.py` | Alignement valeurs dynamiques |

---

## Résultats tests

```
Billing Engine tests:         100/100 passed ✓
Shadow Billing Gas tests:      11/11  passed ✓ (dont 2 nouveaux)
Shadow Expected Elec tests:     8/8   passed ✓
Billing Invariants P0 tests:   36/36  passed ✓
─────────────────────────────────────────────────
TOTAL billing:                155/155 passed ✓
Backend complet:              1 fail pré-existant (hors périmètre billing)
```

---

## Vérification triple

### 1. Calculs vérifiés
- TVA : 0.055 avant 01/08/2025, 0.20 après — conforme LFI 2025 art. 20
- Accise T1 : 30,85 €/MWh (0.03085) au 01/02/2026 — conforme factures ENGIE vérifiées
- Accise T2 : 26,58 €/MWh (0.02658) au 01/02/2026 — conforme LFI 2026
- Capacité : 3,15 €/MW × 1.2 / 8760 = 0,000431 ≈ 0,00043 €/kWh — cohérent
- TDN : 5,52 €/an/Nm³/h × prorata — conforme GRDF

### 2. Logique vérifiée
- Résolution temporelle TVA : ne s'applique pas aux constantes TVA_NORMALE/TVA_REDUITE
- Résolution temporelle accise : chaîne complète T1 et T2 de jan 2025 à fév 2026+
- TDN : conditionnel (débit > 40 + date ≥ 01/07/2026), pas de crash si absent
- Capacité : conditionnel (rate > 0), silencieux si non trouvé
- debit_normalise_nm3h : paramètre optionnel, rétrocompatible

### 3. Sources vérifiées
- TVA : bofip ACTU-2025-00057, service-public.fr, energie-info.fr
- Accise : Loi de finances 2025 + 2026, factures ENGIE/EDF vérifiées
- Capacité : Enchères RTE 06/03/2025 (3,15 €/MW)
- TDN : GRDF sites.grdf.fr/web/terme-debit-normalise, CRE n°2025-161
- VNU : Loi souveraineté énergétique, Enercoop, SIRENergies

---

## Prochaines étapes

1. **CEE** : Modéliser la composante implicite dans le prix fourniture (P6 : 1050 TWhc/an)
2. **Stockage gaz** : Intégrer le terme tarifaire ATS dans la reconstitution gaz
3. **C3 HTA** : Étendre le moteur au segment > 250 kVA
4. **Péréquation gaz** : Préparer convergence tarifaire ELD au 01/07/2026
5. **Réforme capacité** : Adapter le modèle pour l'acheteur unique RTE (nov. 2026)
