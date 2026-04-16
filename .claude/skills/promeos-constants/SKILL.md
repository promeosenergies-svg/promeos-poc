---
name: promeos-constants
description: Constantes métier PROMEOS — valeurs réglementaires et physiques
generated_at: 2026-04-16T21:28:43
---

# Constantes métier PROMEOS — valeurs réglementaires et physiques

## ⚠️ CONSTANTES CRITIQUES (NE JAMAIS MODIFIER EN DUR)

### constants.co2_elec_france
**Facteur CO₂ électricité France**
- **Résumé** : 0.052 kgCO₂e/kWh — ADEME Base Empreinte V23.6 (mix moyen annuel France, ACV)
- **Confiance** : high
- **Source** : ADEME Base Empreinte V23.6

### constants.co2_gaz_france
**Facteur CO₂ gaz naturel France**
- **Résumé** : 0.227 kgCO₂e/kWh — ADEME Base Empreinte V23.6 (PCI, combustion + amont)
- **Confiance** : high
- **Source** : ADEME Base Empreinte V23.6

### constants.accise_elec_t1_2026
**Accise électricité T1 (grande consommation) 2026**
- **Résumé** : 30.85 €/MWh — JORFTEXT000053407616 LFI 2025 art. 20 (fév 2026+)
- **Confiance** : high
- **Source** : JORFTEXT000053407616 — LFI 2025 art. 20

### constants.accise_elec_t2_2026
**Accise électricité T2 (petite consommation) 2026**
- **Résumé** : 26.58 €/MWh — JORFTEXT000053407616 LFI 2025 art. 20 (fév 2026+)
- **Confiance** : high
- **Source** : JORFTEXT000053407616 — LFI 2025 art. 20

### constants.accise_gaz_2026
**Accise gaz naturel 2026**
- **Résumé** : 10.73 €/MWh — JORFTEXT000053407616 LFI 2025 art. 20 (fév 2026+)
- **Confiance** : high
- **Source** : JORFTEXT000053407616 — LFI 2025 art. 20

### constants.dt_penalty_non_conforme
**Pénalité Décret Tertiaire — NON_CONFORME**
- **Résumé** : 7 500 € — Décret n°2019-771 art. R131-38
- **Confiance** : high
- **Source** : Décret n°2019-771 art. R131-38 — Décret Tertiaire

### constants.dt_penalty_a_risque
**Pénalité Décret Tertiaire — A_RISQUE**
- **Résumé** : 3 750 € (50% de réduction vs NON_CONFORME) — Décret n°2019-771
- **Confiance** : high
- **Source** : Décret n°2019-771 art. R131-38 — Décret Tertiaire

### constants.cta_pct_2026
**CTA — part fixe TURPE 2026**
- **Résumé** : 27.04% de la partie fixe TURPE (CRE délibération TURPE 7)
- **Confiance** : high
- **Source** : CRE délibération TURPE 7 — 2026

### constants.coeff_ep_elec_2026
**Coefficient énergie primaire électricité**
- **Résumé** : 1.9 kWhEP/kWhEF — Arrêté du 10 novembre 2023 (janvier 2026)
- **Confiance** : high
- **Source** : Arrêté du 10 novembre 2023 — coefficient énergie primaire

### constants.nebco_threshold_kw
**NEBCO — seuil minimum 100 kW**
- **Résumé** : 100 kW minimum par pas de contrôle (RTE NEBCO, effectif 01/09/2025)
- **Confiance** : high
- **Source** : RTE — NEBCO règles de marché (effectif 01/09/2025)

### constants.bacs_seuil_haut_kw
**BACS — seuil haut CVC 290 kW**
- **Résumé** : 290 kW CVC → obligation BACS au 01/01/2025 (Décret n°2020-887)
- **Confiance** : high
- **Source** : Décret n°2020-887, Art. R175-2
