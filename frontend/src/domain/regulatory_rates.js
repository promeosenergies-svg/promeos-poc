/**
 * regulatory_rates.js — Taux réglementaires SoT côté frontend.
 *
 * @deprecated Sprint C-3 Phase 3.3 (2026-05-04) — utiliser le hook
 *   `useRegulatoryRates()` ou `useRegulatorySource(termId)` depuis
 *   `frontend/src/contexts/RegulatoryRatesContext.jsx` qui fetch
 *   `/api/regulatory/rates` (SoT git versionné `backend/config/sources_reglementaires.yaml`).
 *
 * Ce fichier reste comme **fallback offline** si l'endpoint est non joignable
 * (premier render avant fetch, mode déconnecté, erreur backend). Synchronisation
 * manuelle avec le YAML SoT — vérifié par source-guard FE
 * (regulatory_rates_no_new_consumers_source_guards.test.js : interdit
 * tout NOUVEAU import depuis ce fichier).
 *
 * Retrait définitif planifié Sprint C-7 (polish) si stabilité endpoint confirmée.
 *
 * ─── Historique ───
 * Phase 21.B.1 (audit Phase 17 cumulée P0-NEW-1) : avant cette phase, les taux
 * d'accise/CTA/CSPE/TVA étaient hardcodés inline dans les tooltips de
 * `frontend/src/ui/glossary.js` (ex "26,58 EUR/MWh" en texte). Risque : si la
 * LFI change le taux, le tooltip affiche un faux taux silencieusement.
 *
 * Sprint C-3 Phase 3.3 : la migration vers endpoint API SoT est livrée. Le
 * source-guard backend `test_regulatory_sources_yaml_consistency_with_constants`
 * vérifie la cohérence YAML ↔ doctrine/constants.py runtime.
 *
 * Convention :
 *   - Chaque entrée fournit `value` (numeric), `unit`, `valid_from` (ISO),
 *     `source` (texte avec article réglementaire vérifiable).
 */

export const REGULATORY_RATES = Object.freeze({
  // ─── Accises électricité (Code des impositions) ─────────────────────
  // Valable depuis 1er février 2026 (JORFTEXT000053407616).
  // Cf backend/doctrine/constants.py::ACCISE_ELEC_T2_EUR_PER_MWH = 26.58
  accise_elec_c4_pro: {
    value: 26.58,
    unit: 'EUR/MWh',
    valid_from: '2026-02-01',
    source: 'LFI 2026 + Code des impositions sur les biens et services',
    description: 'Accise électricité professionnels C4 (industriels mid-market)',
  },
  accise_elec_c5_menage: {
    value: 25.09,
    unit: 'EUR/MWh',
    valid_from: '2026-02-01',
    source: 'LFI 2026 + Code des impositions',
    description: 'Accise électricité ménages C5',
  },
  accise_elec_t1: {
    // Tarif normal sans réduction
    value: 30.85,
    unit: 'EUR/MWh',
    valid_from: '2026-02-01',
    source: 'LFI 2026 + Code des impositions',
    description: 'Accise électricité tarif T1 (sans réduction)',
  },

  // ─── Accise gaz naturel ──────────────────────────────────────────────
  accise_gaz: {
    value: 10.73,
    unit: 'EUR/MWh',
    valid_from: '2026-02-01',
    source: 'LFI 2026 + Code des impositions',
    description: 'Accise gaz naturel (TICGN historique)',
  },

  // ─── CTA — Contribution Tarifaire d'Acheminement ────────────────────
  // Phase 24.2 (audit P22 REG-3) : avant ce fix, les coefficients 21,93%
  // et 10,11% étaient annoncés `valid_from: 2026-02-01`, ce qui était
  // contradictoire — le YAML SoT backend (`config/tarifs_reglementaires.
  // yaml::cta`) précise que ces taux historiques (arrêté 26/07/2021) ont
  // expiré le 31/01/2026 et ont été remplacés depuis le 1/02/2026 par
  // 15% (distribution) et 5% (transport ≥50 kV) selon CRE 2026-14.
  // Désormais : valeurs alignées sur le BE actif aujourd'hui (avril 2026).
  cta_elec_distribution: {
    value: 15.0,
    unit: '%',
    valid_from: '2026-02-01',
    source: 'Arrêté CTA 27/01/2026 — CRE délibération 2026-14',
    description: 'CTA électricité — coef sur TURPE fixe distribution (BT/HTA)',
  },
  cta_elec_transport: {
    value: 5.0,
    unit: '%',
    valid_from: '2026-02-01',
    source: 'Arrêté CTA 27/01/2026 — CRE délibération 2026-14',
    description: 'CTA électricité — coef sur TURPE fixe transport (≥50 kV)',
  },
  cta_gaz_distribution: {
    value: 20.8,
    unit: '%',
    valid_from: '2021-08-01',
    source: 'Arrêté CTA 20/07/2021 — coef stable distribution gaz',
    description: 'CTA gaz — coef fixe sur abonnement ATRD annuel',
  },

  // ─── TVA (LFI 2025 art. 278) ────────────────────────────────────────
  tva_normale: {
    value: 20.0,
    unit: '%',
    valid_from: '2025-08-01',
    source: 'CGI art. 278-0 bis + LFI 2025',
    description: 'TVA 20 % uniforme sur tous composants HT facture énergie',
  },
  tva_cta: {
    value: 5.5,
    unit: '%',
    valid_from: '2025-08-01',
    source: 'CGI art. 278-0 bis',
    description: 'TVA réduite 5,5 % sur la CTA',
  },

  // ─── APER — Loi 2023-175 art. 40 + Décret 2022-1726 ────────────────
  // Cf backend/doctrine/constants.py::APER_PENALTY_EUR_PER_M2_PER_YEAR
  aper_penalty: {
    value: 20,
    unit: 'EUR/m²/an',
    valid_from: '2028-01-01',
    source: 'Loi 2023-175 art. 40 + Décret 2022-1726',
    description: 'Sanction APER non engagement solarisation parking',
  },

  // ─── Décret Tertiaire — pénalités annuelles ──────────────────────────
  dt_penalty: {
    value: 7500,
    unit: 'EUR/an/site',
    valid_from: '2030-01-01',
    source: 'Décret n°2019-771 art. 9',
    description: 'Pénalité Décret Tertiaire site non conforme',
  },
  dt_penalty_at_risk: {
    value: 3750,
    unit: 'EUR/an/site',
    valid_from: '2030-01-01',
    source: 'Décret n°2019-771 art. 9',
    description: 'Pénalité Décret Tertiaire site à risque',
  },
  bacs_penalty: {
    value: 1500,
    unit: 'EUR/an/site',
    valid_from: '2027-01-01',
    source: 'Décret n°2020-887',
    description: 'Pénalité BACS site non conforme',
  },
  operat_penalty: {
    value: 1500,
    unit: 'EUR/an/site',
    valid_from: '2024-09-30',
    source: 'Circulaire DGEC 2024 + Décret 2019-771 art. 6',
    description: 'Pénalité OPERAT déclaration manquante',
  },

  // ─── Heuristique marché — prix énergie ETI tertiaire ────────────────
  // Phase 24.3 (audit P22 P1-B) : médiane CRE T4 2025 ETI post-ARENH
  // utilisée pour conversion MWh → €/an dans cards Décision (cohérent
  // backend/doctrine/constants.py::PRICE_ELEC_ETI_2026_EUR_PER_MWH).
  // Non réglementaire stricto sensu mais publiée par la CRE — actualiser
  // au moins T+2 chaque année quand l'observatoire CRE publie le bulletin.
  price_elec_eti_2026: {
    value: 130,
    unit: 'EUR/MWh',
    valid_from: '2026-01-01',
    source: 'Observatoire CRE T4 2025 § ETI tertiaire post-ARENH',
    description: 'Prix marginal énergie ETI tertiaire 2026 — heuristique CRE',
  },
});

/**
 * Helper : renvoie une string formattée FR pour un taux.
 * Ex : `formatRate('accise_elec_c4_pro')` → "26,58 €/MWh"
 */
export function formatRate(key) {
  const r = REGULATORY_RATES[key];
  if (!r) return null;
  const formattedValue =
    r.unit === '%' ? r.value.toFixed(2).replace('.', ',') : r.value.toLocaleString('fr-FR');
  const unit = r.unit === '%' ? ' %' : ` ${r.unit.replace('EUR', '€')}`;
  return `${formattedValue}${unit}`;
}

/**
 * Helper : renvoie un texte tooltip auto-formatté avec source.
 * Ex : `rateTooltip('accise_elec_c4_pro')` →
 *   "26,58 €/MWh (depuis 01/02/2026) · LFI 2026 + Code des impositions"
 */
export function rateTooltip(key) {
  const r = REGULATORY_RATES[key];
  if (!r) return null;
  const dateFR = new Date(r.valid_from).toLocaleDateString('fr-FR');
  return `${formatRate(key)} (depuis ${dateFR}) · ${r.source}`;
}
