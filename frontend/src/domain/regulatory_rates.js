/**
 * regulatory_rates.js — Taux réglementaires SoT côté frontend.
 *
 * Phase 21.B.1 (audit Phase 17 cumulée P0-NEW-1) : avant cette phase,
 * les taux d'accise/CTA/CSPE/TVA étaient hardcodés inline dans les
 * tooltips de `frontend/src/ui/glossary.js` (ex "26,58 EUR/MWh" en
 * texte). Risque : si la LFI change le taux, le tooltip affiche un
 * faux taux silencieusement.
 *
 * Désormais : valeurs centralisées ici, avec date d'effet et source
 * réglementaire visible. À chaque revalorisation, mettre à jour ce
 * fichier + ajouter une entrée historique (commentaire valid_until).
 *
 * Cohérence backend : ces valeurs MIRROIR `backend/doctrine/constants.py`.
 * Si tu modifies ici, modifie aussi le backend (ou inversement). À terme,
 * les valeurs devraient être servies par un endpoint API
 * `/api/regulatory/rates` qui lit ParameterStore versionné — Phase 22.
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
  // Coefficients 2026 (arrêté CRE) — pré-février 2026 : 15 %/5 %.
  cta_elec_gestion: {
    value: 21.93,
    unit: '%',
    valid_from: '2026-02-01',
    source: 'Code de la sécurité sociale + arrêté CRE',
    description: 'CTA électricité — coef sur part gestion TURPE',
  },
  cta_elec_abonnement: {
    value: 10.11,
    unit: '%',
    valid_from: '2026-02-01',
    source: 'Arrêté CRE',
    description: 'CTA électricité — coef sur abonnement TURPE',
  },
  cta_gaz_fixe: {
    value: 20.8,
    unit: '%',
    valid_from: '2026-02-01',
    source: 'Arrêté CRE',
    description: 'CTA gaz — coefficient fixe',
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
