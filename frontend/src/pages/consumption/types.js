/**
 * PROMEOS — Explorer Motor: shared type constants
 */

export const MODES = {
  AGREGE: 'agrege',
  SUPERPOSE: 'superpose',
  EMPILE: 'empile',
  SEPARE: 'separe',
};

export const UNITS = {
  KWH: 'kwh',
  KW: 'kw',
  EUR: 'eur',
};

export const LAYERS = {
  TALON: 'talon',
  METEO: 'meteo',
  SIGNATURE: 'signature',
  TUNNEL: 'tunnel',
  OBJECTIFS: 'objectifs',
};

export const DEFAULT_LAYERS = {
  [LAYERS.TALON]: false,
  [LAYERS.METEO]: false,
  [LAYERS.SIGNATURE]: false,
  [LAYERS.TUNNEL]: true,
  [LAYERS.OBJECTIFS]: false,
};

export const MODE_LABELS = {
  [MODES.AGREGE]: 'Agrege',
  [MODES.SUPERPOSE]: 'Superpose',
  [MODES.EMPILE]: 'Empile',
  [MODES.SEPARE]: 'Separe',
};

export const UNIT_LABELS = {
  [UNITS.KWH]: 'kWh',
  [UNITS.KW]: 'kW',
  [UNITS.EUR]: 'EUR',
};

export const LAYER_LABELS = {
  [LAYERS.TALON]: 'Talon',
  [LAYERS.METEO]: 'Meteo',
  [LAYERS.SIGNATURE]: 'Signature',
  [LAYERS.TUNNEL]: 'Tunnel P10-P90',
  [LAYERS.OBJECTIFS]: 'Objectifs',
};

/** Max sites selectable simultaneously in multi-site mode */
export const MAX_SITES = 5;

/**
 * Energy-type-aware unit label.
 * Gas backend returns kWh PCS — we display "kWh PCS" for clarity.
 * @param {'kwh'|'kw'|'eur'} unit
 * @param {'electricity'|'gas'} energyType
 * @returns {string}
 */
export function unitLabel(unit, energyType) {
  if (energyType === 'gas') {
    if (unit === 'kwh') return 'kWh PCS';
    if (unit === 'kw') return 'kW PCS';
  }
  return UNIT_LABELS[unit] || unit;
}

/**
 * Tabs that are NOT applicable for the given energyType.
 * @param {string} energyType
 * @returns {Set<string>}
 */
export function nonApplicableTabs(energyType) {
  if (energyType === 'gas') return new Set(['hphc', 'tunnel', 'targets', 'signature']);
  return new Set(['gas']);
}
