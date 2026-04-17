# SME Review Checklist -- Items KB PROMEOS

## Pour chaque item namespace=constants ou regulations

### Verification source
- [ ] La valeur vient d'un texte officiel (JORF, CRE, ADEME, RTE)
- [ ] La reference exacte est citee (numero de decret, article, date)
- [ ] La date de validite est correcte (valid_from / valid_until)
- [ ] Le fichier source Python/YAML reference existe bien dans le repo

### Verification technique
- [ ] L'unite est correcte et explicite (EUR/MWh != EUR/kWh != kgCO2/kWh)
- [ ] Aucune confusion possible avec d'autres valeurs proches
- [ ] Le critical_warning est present si risque de confusion
- [ ] La formule est correcte et testable

### Verification agent
- [ ] agent_context.summary est actionnable en 1 phrase
- [ ] user_explanation.short est comprehensible par un DAF non expert
- [ ] Le tooltip contient la source (visible dans l'UI)

### Verification lifecycle
- [ ] status=validated (jamais validated+confidence=low)
- [ ] version respecte le format YYYY.N
- [ ] Pas de doublon avec un item existant

---

## Constantes validees (11 items)

| ID | Valeur | Source | SME |
|----|--------|--------|-----|
| constants.co2_elec_france | 0.052 kgCO2e/kWh | ADEME V23.6 | [ ] |
| constants.co2_gaz_france | 0.227 kgCO2e/kWh | ADEME V23.6 | [ ] |
| constants.accise_elec_t1_2026 | 30.85 EUR/MWh | JORF LFI 2025 art.20 | [ ] |
| constants.accise_elec_t2_2026 | 26.58 EUR/MWh | JORF LFI 2025 art.20 | [ ] |
| constants.accise_gaz_2026 | 10.73 EUR/MWh | JORF LFI 2025 art.20 | [ ] |
| constants.cta_pct_2026 | 27.04% | CRE TURPE 7 | [ ] |
| constants.coeff_ep_elec_2026 | 1.9 kWhEP/kWhEF | Arrete 10/11/2023 | [ ] |
| constants.nebco_threshold_kw | 100 kW | RTE NEBCO 01/09/2025 | [ ] |
| constants.dt_penalty_non_conforme | 7500 EUR | Decret 2019-771 R131-38 | [ ] |
| constants.dt_penalty_a_risque | 3750 EUR | Decret 2019-771 R131-38 | [ ] |
| constants.bacs_seuil_haut_kw | 290 kW | Decret 2020-887 R175-2 | [ ] |

## Constantes a revalider en 2027

- constants.co2_elec_france -- Prochaine mise a jour ADEME
- constants.accise_elec_t1_2026 -- Revoir au vote budget 2027
- constants.cta_pct_2026 -- Revoir a la prochaine deliberation CRE
