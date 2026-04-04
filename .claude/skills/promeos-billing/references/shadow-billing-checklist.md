# Shadow Billing — Checklist complète de vérification

## Phase 1 : Vérifications structurelles (M+7 après réception facture)

- [ ] **PDL/PCE match** — Le point de livraison sur la facture = registre PROMEOS
  - Source: Enedis SGE ou DataConnect
  - Anomalie BILL_002 si mismatch
- [ ] **Puissance souscrite match** — Facture vs contrat Enedis
  - Vérifier via flux F12 ou portail Enedis
  - Anomalie BILL_002 si ≠
- [ ] **Option tarifaire correcte** — HP/HC, Base, HPHC, etc.
  - Cohérent avec TOUSchedule PROMEOS
  - Anomalie BILL_003 si ≠
- [ ] **Période de facturation** — Entre 28 et 31 jours
  - Régularisation acceptable si période plus longue
  - Flag si < 25 jours ou > 35 jours

## Phase 2 : Vérifications consommation (M+10)

- [ ] **Index cohérent** — Index fin - index début = consommation annoncée
  - Tolérance: ±0.5%
  - Anomalie si écart > 1%
- [ ] **Conso vs historique** — ±3% vs même période N-1
  - Hors événement documenté (travaux, covid, changement activité)
  - Si > +10% → investigation automatique
- [ ] **Index estimé vs réel** — Si facture avec index estimé
  - Comparer avec CDC Enedis réelle
  - Flag profilage si écart > 5%
- [ ] **Pas de doublon** — Pas de compteur relevé + estimé simultanément
  - Anomalie BILL_006 (CRITICAL) si détecté

## Phase 3 : Vérifications financières (M+12)

- [ ] **Fourniture énergie** — prix_contrat × volume par période
  - Utiliser resolve_pricing(annexe) pour le prix effectif
  - Par période: HPH, HCH, HPB, HCB, Pointe
  - Tolérance: ±2%
  - Anomalie BILL_001 si écart > 5%
- [ ] **Acheminement TURPE** — Grille en vigueur à date M
  - TURPE 6 si facture < 01/08/2025
  - TURPE 7 si facture ≥ 01/08/2025
  - Anomalie BILL_008 si version incorrecte
- [ ] **Accise** — 25.79 €/MWh × volume (Loi finances 2025, art. L312-35 CGI)
  - Anomalie BILL_004 si taux ≠ 25.79
- [ ] **CTA** — 27.04% × part fixe TURPE (Arrêté du 26/04/2023)
  - Vérifier assiette de calcul
- [ ] **TVA** — 5.5% sur (abonnement + CTA), 20% sur (conso + accise + CEE + capacité)
  - Anomalie BILL_007 si répartition incorrecte
- [ ] **CEE** — Montant cohérent avec obligation fournisseur
  - Variable selon fournisseur, ~0.478 €/MWh indicatif
- [ ] **Capacité** — Période de couverture correcte (hiver Nov-Mars)

## Phase 4 : Alertes et Reclaim (M+14)

- [ ] **Seuil alerte** — Écart recalcul vs facturé
  - > 2 €/MWh → erreur probable → marquer pour investigation
  - > 5% du montant total → reclaim recommandé
- [ ] **Surconsommation** — Conso > baseline +10%
  - Chercher cause: météo (DJU), occupation, équipement, fuite
- [ ] **Régularisation anormale** — Régul > 50% de la facture précédente
  - Vérifier période de régularisation et index

## Phase 5 : Procédure Reclaim (M+20)

1. Compiler dossier: screenshot facture, calcul correct, impact € (Réf: Art. L224-11 Code de la consommation)
2. Lettre recommandée au fournisseur avec détails PDL, erreur, montant
3. Délai légal de réponse: 30 jours
4. Si pas de réponse → Médiateur National de l'Énergie (2 mois max)
5. Demander avoir + intérêts de retard

## Formules de recalcul

```
montant_fourniture = Σ (volume_periode × prix_periode)
montant_turpe = abonnement_turpe + Σ (volume_periode × tarif_soutirage_periode)
montant_accise = volume_total × 0.02579  # en €/kWh
montant_cta = 0.2704 × part_fixe_turpe
montant_ht = montant_fourniture + montant_turpe + montant_accise + montant_cta + montant_cee + montant_capacite
montant_tva_reduit = (abonnement_fourniture + montant_cta) × 0.055
montant_tva_plein = (montant_ht - abonnement_fourniture - montant_cta) × 0.20
montant_ttc = montant_ht + montant_tva_reduit + montant_tva_plein
```
