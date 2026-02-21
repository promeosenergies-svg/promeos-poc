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
