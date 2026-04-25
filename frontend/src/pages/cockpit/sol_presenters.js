/**
 * PROMEOS — sol_presenters.js
 *
 * Helpers PUREMENT présentation pour CockpitSol (Phase 2).
 * Aucun fetch, aucun appel API, aucun accès store. Fonctions déterministes.
 *
 * Complète sol_interpreters.jsx (qui contient uniquement les helpers JSX) :
 * ici, les helpers de formatage / transformation de données / calculs simples.
 *
 * Typographie FR :
 * - NBSP (U+00A0) insécable : "24 h", "sem. 16"
 * - NNBSP (U+202F) fine insécable : "1 847,20 €", "14 h 32"
 */

export const NBSP = '\u00A0';
export const NNBSP = '\u202F';

// ─────────────────────────────────────────────────────────────────────────────
// TODO backend — hors scope refonte (PR séparé sur main)
//
// Deux endpoints manquent pour afficher les deltas N-1 sur les KPIs Cockpit :
//
//   1. getBillingCompareMonthly(params) — retourne { current_month_eur,
//      previous_month_eur } pour calculer le delta facture énergie.
//      Backend existe partiellement (/billing/compare-monthly), à élargir
//      pour exposer previous_month_eur directement dans /billing/summary.
//
//   2. getCockpitConsoMonth() — retourne { current_mwh, previous_year_mwh }
//      pour calculer le delta conso vs N-1. L'endpoint /cockpit/conso-month
//      existe mais retourne seulement le mois courant, pas N-1.
//
// En attendant, CockpitSol passe delta={null} pour ces deux KPIs et
// SolKpiCard rend conditionnellement la pastille (pas de "—" disgracieux).
// ─────────────────────────────────────────────────────────────────────────────

// ─────────────────────────────────────────────────────────────────────────────
// Kickers / scope labels
// ─────────────────────────────────────────────────────────────────────────────

/**
 * "Cockpit · semaine 16 · patrimoine HELIOS — 5 sites"
 * (le suffixe "— N sites" n'apparaît que si scope.sitesCount est fourni)
 */
export function buildKicker({ module = 'Cockpit', weekNum, scope, date = new Date() } = {}) {
  const week = weekNum ?? computeIsoWeek(date);
  const orgName = scope?.orgName || 'votre patrimoine';
  const sitesCount = scope?.sitesCount;
  const sitesSuffix =
    sitesCount != null && sitesCount > 0
      ? ` — ${sitesCount}${NBSP}site${sitesCount > 1 ? 's' : ''}`
      : '';
  return `${module} · semaine ${week} · patrimoine ${orgName}${sitesSuffix}`;
}

/**
 * "Votre cockpit énergétique, semaine du 14 avril."
 */
export function buildPanelDesc({ date = new Date() } = {}) {
  const day = date.getDate();
  const monthNames = [
    'janvier',
    'février',
    'mars',
    'avril',
    'mai',
    'juin',
    'juillet',
    'août',
    'septembre',
    'octobre',
    'novembre',
    'décembre',
  ];
  const month = monthNames[date.getMonth()];
  return `Votre cockpit énergétique, semaine du ${day}${NBSP}${month}.`;
}

/**
 * "Sem. 16 · avril"
 */
export function buildWeekLabel(date = new Date()) {
  const weekNum = computeIsoWeek(date);
  const monthShort = [
    'janv.',
    'févr.',
    'mars',
    'avril',
    'mai',
    'juin',
    'juil.',
    'août',
    'sept.',
    'oct.',
    'nov.',
    'déc.',
  ][date.getMonth()];
  return `Sem.${NBSP}${weekNum} · ${monthShort}`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Time / semaine ISO
// ─────────────────────────────────────────────────────────────────────────────

/** ISO 8601 week number */
export function computeIsoWeek(date = new Date()) {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  const dayNum = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  return Math.ceil(((d - yearStart) / 86400000 + 1) / 7);
}

/**
 * Heure locale au format "14 h 32" (NBSP).
 */
export function formatHourMinute(date = new Date()) {
  const h = String(date.getHours()).padStart(2, '0');
  const m = String(date.getMinutes()).padStart(2, '0');
  return `${h}${NBSP}h${NBSP}${m}`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Tarif HP/HC simplifié — grille standard FR (HP 6h→22h, HC sinon)
// ─────────────────────────────────────────────────────────────────────────────

const DEFAULT_HP_START = 6;
const DEFAULT_HP_END = 22;

/**
 * Retourne { period: 'HP'|'HC', endsAt: string } pour une date donnée.
 * Week-end considéré HC entier (convention FR standard).
 */
export function getCurrentTariffPeriod(date = new Date(), opts = {}) {
  const hpStart = opts.hpStart ?? DEFAULT_HP_START;
  const hpEnd = opts.hpEnd ?? DEFAULT_HP_END;
  const isWeekend = [0, 6].includes(date.getDay());
  const hour = date.getHours();
  const inHp = !isWeekend && hour >= hpStart && hour < hpEnd;
  if (inHp) {
    return { period: 'HP', endsAt: `${hpEnd}${NBSP}h` };
  }
  // HC : endsAt = prochain passage HP
  if (isWeekend || hour < hpStart) {
    return { period: 'HC', endsAt: `${hpStart}${NBSP}h` };
  }
  return { period: 'HC', endsAt: `minuit` };
}

// ─────────────────────────────────────────────────────────────────────────────
// Deltas — formatage pour SolKpiCard
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Formate un delta (ratio ou points).
 * @param {{ current, previous, unit, context }} input
 *   - current, previous : number
 *   - unit : '%' | 'pts'
 *   - context : "vs février" (ajouté en suffixe)
 * @returns {{ direction: 'up'|'down'|'flat', text: string, value: number }}
 */
export function computeDelta({ current, previous, unit = '%', context = '' } = {}) {
  if (current == null || previous == null || previous === 0) {
    return { direction: 'flat', text: '—', value: 0 };
  }
  let value;
  let text;
  if (unit === 'pts') {
    value = current - previous;
    const sign = value >= 0 ? '+' : '−';
    text = `${sign}${Math.abs(value).toFixed(0)}${NBSP}pts`;
  } else {
    value = (current - previous) / previous;
    const pct = Math.abs(value * 100);
    const sign = value >= 0 ? '+' : '−';
    const formatted = pct.toFixed(1).replace('.', ',');
    text = `${sign}${formatted}${NBSP}%`;
  }
  const direction =
    Math.abs(value) < (unit === 'pts' ? 0.5 : 0.005) ? 'flat' : value > 0 ? 'up' : 'down';
  const arrow = direction === 'up' ? '▲' : direction === 'down' ? '▼' : '—';
  return {
    direction,
    value,
    text: context ? `${arrow} ${text} ${context}` : `${arrow} ${text}`,
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// Série horaire — pic + part HP/HC
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Retourne le pic (max value) d'une série {time, value}.
 * @returns {{ time, value, label }|null}
 */
export function findPeak(series = [], unit = 'kW') {
  if (!Array.isArray(series) || series.length === 0) return null;
  let peak = series[0];
  for (const pt of series) {
    if (pt?.value != null && pt.value > (peak?.value ?? -Infinity)) peak = pt;
  }
  if (peak?.value == null) return null;
  const hourLabel =
    typeof peak.time === 'string' && peak.time.includes(':') ? peak.time.split(':')[0] : peak.time;
  return {
    time: peak.time,
    value: peak.value,
    label: `pic ${hourLabel}${NBSP}h · ${peak.value}${NBSP}${unit}`,
  };
}

/**
 * Calcule la part HP d'une série de puissances (proxy consommation).
 * @param {Array<{time, value}>} series
 * @param {{ hpStart, hpEnd }} opts
 * @returns {number} ratio 0..1
 */
export function computeHPShare(series = [], opts = {}) {
  if (!Array.isArray(series) || series.length === 0) return 0;
  const hpStart = opts.hpStart ?? DEFAULT_HP_START;
  const hpEnd = opts.hpEnd ?? DEFAULT_HP_END;
  let hpSum = 0;
  let totalSum = 0;
  for (const pt of series) {
    if (pt?.value == null) continue;
    const hour = parseInt(String(pt.time).split(':')[0], 10);
    if (isNaN(hour)) continue;
    totalSum += pt.value;
    if (hour >= hpStart && hour < hpEnd) hpSum += pt.value;
  }
  if (totalSum === 0) return 0;
  return hpSum / totalSum;
}

// ─────────────────────────────────────────────────────────────────────────────
// Formatters FR
// ─────────────────────────────────────────────────────────────────────────────

/**
 * "47 382" (NNBSP fine insécable en sep milliers)
 */
export function formatFR(value, decimals = 0) {
  if (value == null || isNaN(value)) return '—';
  const fixed = Number(value).toFixed(decimals);
  const [intPart, fracPart] = fixed.split('.');
  const intWithSep = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, NNBSP);
  return fracPart ? `${intWithSep},${fracPart}` : intWithSep;
}

/**
 * "1 847 €" avec NNBSP avant €
 */
export function formatFREur(value, decimals = 0) {
  if (value == null || isNaN(value)) return '—';
  return `${formatFR(value, decimals)}${NBSP}€`;
}

/**
 * "85 %" avec NBSP
 */
export function formatFRPct(value, decimals = 0) {
  if (value == null || isNaN(value)) return '—';
  return `${formatFR(value, decimals)}${NBSP}%`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Week cards mapping — transforme notifications backend → SolWeekCard props
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Mappe 3 signaux hétérogènes (alerte dérive / échéance à faire / validation succès)
 * en 3 SolWeekCard props.
 * @param {{ alerts, upcomingItems, validatedItems }} inputs
 * @returns {Array<{ id, tagKind, tagLabel, title, body, footerLeft, footerRight, onClick }>}
 */
export function buildWeekSignals({
  alerts = [],
  upcomingItems = [],
  validatedItems = [],
  scope = {},
  onNavigate = null, // Fix P4.5 : callback pour gérer string deeplink → fonction navigate
} = {}) {
  const cards = [];

  // Helper : convertit deeplink string → fonction ou undefined (React n'accepte
  // pas un string comme onClick — warning console). Si onNavigate callback fourni,
  // l'utilise (React Router) ; sinon window.location fallback.
  const asNavigateFn = (path) => {
    if (!path || typeof path !== 'string') return undefined;
    if (typeof onNavigate === 'function') return () => onNavigate(path);
    return () => {
      if (typeof window !== 'undefined') window.location.assign(path);
    };
  };

  // 1) À regarder — alerte la plus critique
  const topAlert = alerts[0];
  if (topAlert) {
    const impact = topAlert.estimated_impact_eur ?? topAlert.impact_eur;
    cards.push({
      id: `alert-${topAlert.id || 0}`,
      tagKind: 'attention',
      tagLabel: 'À regarder',
      title: topAlert.title || topAlert.label || 'Alerte à surveiller',
      body: topAlert.message || topAlert.summary || topAlert.description,
      footerLeft: impact ? `chiffré : ${formatFR(impact, 0)} €` : '',
      footerRight: topAlert.automatable ? 'Automatisable' : '⌘K',
      onClick: asNavigateFn(topAlert.deeplink_path || topAlert.navigateTo),
    });
  } else {
    // Fallback attention : invitation à importer des données
    cards.push({
      id: 'alert-fallback',
      tagKind: 'attention',
      tagLabel: 'À regarder',
      title: 'Aucune alerte critique cette semaine',
      body: 'Votre patrimoine tourne au rythme attendu. Sol veille en continu.',
      footerLeft: 'Détection automatique active',
      footerRight: '✓ Stable',
    });
  }

  // 2) À faire — prochaine échéance réglementaire
  const topUpcoming = upcomingItems[0];
  if (topUpcoming) {
    const deadline = topUpcoming.deadline || topUpcoming.dueDate || topUpcoming.echeance;
    const penalty = topUpcoming.penalty_eur;
    const sitesCount = topUpcoming.sites_concerned;
    cards.push({
      id: `upcoming-${topUpcoming.id || 0}`,
      tagKind: 'afaire',
      tagLabel: 'À faire',
      title: topUpcoming.label || topUpcoming.title || 'Échéance à préparer',
      body:
        (topUpcoming.description || topUpcoming.summary || '') +
        (sitesCount
          ? ` ${sitesCount} site${sitesCount > 1 ? 's' : ''} concerné${sitesCount > 1 ? 's' : ''}.`
          : ''),
      footerLeft: deadline ? `échéance ${deadline}` : '',
      footerRight: penalty ? `pénalité ${formatFR(penalty, 0)} €` : 'Automatisable',
      onClick: asNavigateFn(topUpcoming.deeplink_path || topUpcoming.navigateTo),
    });
  } else {
    cards.push({
      id: 'upcoming-fallback',
      tagKind: 'afaire',
      tagLabel: 'À faire',
      title: 'Aucune échéance sous 90 jours',
      body: 'Votre calendrier réglementaire est à jour pour le trimestre.',
      footerLeft: 'Veille réglementaire active',
      footerRight: '✓ Clean',
    });
  }

  // 3) Bonne nouvelle — dernière validation / signal positif
  const topValidated = validatedItems[0];
  if (topValidated) {
    cards.push({
      id: `validated-${topValidated.id || 0}`,
      tagKind: 'succes',
      tagLabel: 'Bonne nouvelle',
      title: topValidated.label || topValidated.title,
      body: topValidated.description || topValidated.summary,
      footerLeft: 'conforme · pièce au dossier',
      footerRight: '✓ Clean',
      onClick: asNavigateFn(topValidated.deeplink_path || topValidated.navigateTo),
    });
  } else {
    // Fallback succès : toujours donner une bonne nouvelle — déséquilibre visuel sinon
    const sitesCount = scope.sitesCount;
    cards.push({
      id: 'validated-fallback',
      tagKind: 'succes',
      tagLabel: 'Bonne nouvelle',
      title: sitesCount
        ? `Vos ${sitesCount} sites sont pilotés par PROMEOS`
        : 'Votre patrimoine est sous surveillance',
      body: 'Détection automatique, audit traçable, voix Sol prête à préparer vos courriers.',
      footerLeft: 'Sol · en veille',
      footerRight: '✓ Opérationnel',
    });
  }

  return cards;
}

// ─────────────────────────────────────────────────────────────────────────────
// Freshness — "actualisé il y a 47 min"
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Formate une ancienneté en phrase FR.
 * @param {Date|string|number} timestamp
 * @returns {string} ex "il y a 47 min", "il y a 2 h", "il y a 3 j"
 */
export function freshness(timestamp, now = new Date()) {
  if (!timestamp) return 'à l\u2019instant';
  const past = timestamp instanceof Date ? timestamp : new Date(timestamp);
  if (isNaN(past.getTime())) return 'à l\u2019instant';
  const diffMs = now.getTime() - past.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return 'à l\u2019instant';
  if (diffMin < 60) return `il y a ${diffMin}${NBSP}min`;
  const diffH = Math.floor(diffMin / 60);
  if (diffH < 24) return `il y a ${diffH}${NBSP}h`;
  const diffJ = Math.floor(diffH / 24);
  return `il y a ${diffJ}${NBSP}j`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Load curve — mock 24h fallback quand EMS vide
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Courbe 24h générée déterministiquement pour servir de signature visuelle
 * même en l'absence de données EMS horaires. Pattern bureau : creux nuit,
 * rampe matinale, plateau journée, pic après-midi, redescente soirée.
 * @returns {Array<{time, value}>}
 */
export function buildFallbackLoadCurve() {
  const pattern = [
    18,
    17,
    16,
    15,
    15,
    16, // 00–05 nuit
    22,
    38,
    62,
    85,
    98,
    108, // 06–11 rampe matinale
    112,
    115,
    118,
    116,
    110,
    96, // 12–17 plateau + pic
    78,
    58,
    42,
    32,
    26,
    22, // 18–23 redescente
  ];
  return pattern.map((value, hour) => ({
    time: `${String(hour).padStart(2, '0')}:00`,
    value,
  }));
}

// ─────────────────────────────────────────────────────────────────────────────
// Series transforms — EMS timeseries → SolLoadCurve shape
// ─────────────────────────────────────────────────────────────────────────────

/**
 * EMS backend → SolLoadCurve : [{ t, v }] → [{ time: 'HH:MM', value }]
 */
export function adaptEmsSeriesToLoadCurve(emsPoints = []) {
  if (!Array.isArray(emsPoints)) return [];
  return emsPoints
    .map((pt) => {
      const raw = pt?.t ?? pt?.timestamp ?? pt?.time;
      if (!raw) return null;
      const normalized = typeof raw === 'string' ? raw.replace(' ', 'T') : raw;
      const d = new Date(normalized);
      if (isNaN(d.getTime())) return null;
      const h = String(d.getHours()).padStart(2, '0');
      const m = String(d.getMinutes()).padStart(2, '0');
      const value = pt?.v ?? pt?.value;
      if (value == null || isNaN(value)) return null;
      return { time: `${h}:${m}`, value: Math.round(value) };
    })
    .filter(Boolean);
}
