/**
 * PROMEOS — Tests unitaires des presenters Sol (Phase 5 L4)
 *
 * DoD criterion 4 (reporté depuis Phase 2) : chaque fichier
 * pages/*\/sol_presenters.js contient des fonctions pures déterministes
 * qui méritent une couverture unitaire.
 *
 * Scope :
 *   - Formatters FR (formatFR, formatFREur, formatFRPct)
 *   - Calculs (computeDelta, freshness, findPeak, computeHPShare)
 *   - Transformers (buildKicker, buildWeekSignals)
 *   - Interpreters (interpretScoreDT, interpretScoreBACS, interpretScoreAPER,
 *     interpretPrixPondere, interpretEcheance, deriveScoreFromFindings)
 *   - Fallbacks (businessErrorFallback avec slot désambiguïsation)
 *
 * Aucun test sur business logic backend — uniquement transforms.
 */
import { describe, it, expect } from 'vitest';
import {
  NBSP,
  NNBSP,
  formatFR,
  formatFREur,
  formatFRPct,
  computeDelta,
  freshness,
  findPeak,
  computeHPShare,
  buildKicker,
  buildFallbackLoadCurve,
  computeIsoWeek,
  getCurrentTariffPeriod,
  adaptEmsSeriesToLoadCurve,
} from '../cockpit/sol_presenters';
import {
  deriveScoreFromFindings,
  computeScoreDelta,
  buildConformiteNarrative,
} from '../conformite/sol_presenters';
import {
  interpretEcheance,
  interpretPrixPondere,
  estimateWeightedPrice,
  synthesizeMarketTrend,
  detectOpportunityArea,
} from '../achat/sol_presenters';
import {
  computeSiteEui,
  computeAvgEui,
  computeAvgBenchmark,
  topEuiDrivers,
} from '../patrimoine/sol_presenters';
import {
  extractCurrentMonthTotals,
  estimateRecoveredYtd,
  countContestableAnomalies,
  adaptCompareToBarChart,
} from '../bill-intel/sol_presenters';
import {
  businessErrorFallback,
  BUSINESS_ERRORS,
} from '../../i18n/business_errors';

// ══════════════════════════════════════════════════════════════════════════
// Formatters FR
// ══════════════════════════════════════════════════════════════════════════

describe('formatFR', () => {
  it('entier avec séparateur NNBSP milliers', () => {
    expect(formatFR(47382)).toBe(`47${NNBSP}382`);
  });
  it('décimal avec virgule FR', () => {
    expect(formatFR(12.5, 1)).toBe('12,5');
    expect(formatFR(1847.2, 2)).toBe(`1${NNBSP}847,20`);
  });
  it('zéro rendu', () => {
    expect(formatFR(0)).toBe('0');
  });
  it('null / NaN → "—"', () => {
    expect(formatFR(null)).toBe('—');
    expect(formatFR(undefined)).toBe('—');
    expect(formatFR(NaN)).toBe('—');
  });
});

describe('formatFREur', () => {
  it('ajoute NBSP + €', () => {
    expect(formatFREur(1847)).toBe(`1${NNBSP}847${NBSP}€`);
  });
  it('gère null', () => {
    expect(formatFREur(null)).toBe('—');
  });
});

describe('formatFRPct', () => {
  it('ajoute NBSP + %', () => {
    expect(formatFRPct(85)).toBe(`85${NBSP}%`);
    expect(formatFRPct(12.5, 1)).toBe(`12,5${NBSP}%`);
  });
});

// ══════════════════════════════════════════════════════════════════════════
// computeDelta
// ══════════════════════════════════════════════════════════════════════════

describe('computeDelta', () => {
  it('hausse pct → direction up + flèche ▲', () => {
    const d = computeDelta({ current: 110, previous: 100, unit: '%' });
    expect(d.direction).toBe('up');
    expect(d.text).toMatch(/▲/);
    expect(d.text).toMatch(/\+10,0/);
  });
  it('baisse pct → direction down + flèche ▼', () => {
    const d = computeDelta({ current: 90, previous: 100, unit: '%' });
    expect(d.direction).toBe('down');
    expect(d.text).toMatch(/▼/);
  });
  it('delta plat → direction flat + —', () => {
    const d = computeDelta({ current: 100, previous: 100 });
    expect(d.direction).toBe('flat');
  });
  it('unit pts (entier) au lieu de pct', () => {
    const d = computeDelta({ current: 65, previous: 58, unit: 'pts' });
    expect(d.text).toMatch(/pts/);
    expect(d.direction).toBe('up');
  });
  it('previous null → "—"', () => {
    const d = computeDelta({ current: 100, previous: null });
    expect(d.text).toBe('—');
  });
  it('context suffix ajouté', () => {
    const d = computeDelta({ current: 110, previous: 100, context: 'vs février' });
    expect(d.text).toMatch(/vs février/);
  });
});

// ══════════════════════════════════════════════════════════════════════════
// freshness
// ══════════════════════════════════════════════════════════════════════════

describe('freshness', () => {
  const now = new Date('2026-04-19T12:00:00Z');
  it('il y a X min', () => {
    const past = new Date('2026-04-19T11:13:00Z');
    expect(freshness(past, now)).toMatch(/47.*min/);
  });
  it('il y a X h', () => {
    const past = new Date('2026-04-19T08:00:00Z');
    expect(freshness(past, now)).toMatch(/4.*h/);
  });
  it('il y a X j', () => {
    const past = new Date('2026-04-15T12:00:00Z');
    expect(freshness(past, now)).toMatch(/4.*j/);
  });
  it('null → à l\'instant', () => {
    expect(freshness(null)).toMatch(/instant/);
  });
});

// ══════════════════════════════════════════════════════════════════════════
// findPeak + computeHPShare
// ══════════════════════════════════════════════════════════════════════════

describe('findPeak', () => {
  it('retourne le max avec time + value + label', () => {
    const series = [
      { time: '00:00', value: 40 },
      { time: '14:00', value: 118 },
      { time: '22:00', value: 45 },
    ];
    const peak = findPeak(series);
    expect(peak.value).toBe(118);
    expect(peak.time).toBe('14:00');
    expect(peak.label).toMatch(/pic 14/);
  });
  it('série vide → null', () => {
    expect(findPeak([])).toBeNull();
    expect(findPeak(null)).toBeNull();
  });
});

describe('computeHPShare', () => {
  it('calcule la part HP (6-22h) en ratio 0-1', () => {
    const series = [
      { time: '02:00', value: 40 }, // HC
      { time: '10:00', value: 100 }, // HP
      { time: '14:00', value: 100 }, // HP
      { time: '23:00', value: 40 }, // HC
    ];
    const share = computeHPShare(series);
    // HP = 200, total = 280, ratio = 0,714
    expect(share).toBeCloseTo(0.714, 2);
  });
  it('série vide → 0', () => {
    expect(computeHPShare([])).toBe(0);
  });
});

// ══════════════════════════════════════════════════════════════════════════
// buildKicker
// ══════════════════════════════════════════════════════════════════════════

describe('buildKicker', () => {
  it('format standard avec orgName + sitesCount', () => {
    const kicker = buildKicker({
      module: 'Cockpit',
      weekNum: 16,
      scope: { orgName: 'HELIOS', sitesCount: 5 },
    });
    expect(kicker).toContain('Cockpit');
    expect(kicker).toContain('semaine 16');
    expect(kicker).toContain('HELIOS');
    expect(kicker).toMatch(/5.*sites/);
  });
  it('sans sitesCount → pas de suffixe', () => {
    const kicker = buildKicker({ module: 'Conformité', weekNum: 16, scope: { orgName: 'HELIOS' } });
    expect(kicker).not.toMatch(/—.*sites/);
  });
  it('défaut scope → "votre patrimoine"', () => {
    const kicker = buildKicker({ weekNum: 1 });
    expect(kicker).toContain('votre patrimoine');
  });
});

describe('computeIsoWeek', () => {
  it('retourne un entier 1-53', () => {
    const week = computeIsoWeek(new Date('2026-04-15'));
    expect(Number.isInteger(week)).toBe(true);
    expect(week).toBeGreaterThanOrEqual(1);
    expect(week).toBeLessThanOrEqual(53);
  });
});

describe('getCurrentTariffPeriod', () => {
  it('14h jour ouvré → HP', () => {
    // Mardi 2026-04-14 14h00
    const d = new Date(2026, 3, 14, 14, 0);
    expect(getCurrentTariffPeriod(d).period).toBe('HP');
  });
  it('3h jour ouvré → HC', () => {
    const d = new Date(2026, 3, 14, 3, 0);
    expect(getCurrentTariffPeriod(d).period).toBe('HC');
  });
  it('samedi 14h → HC (week-end entier)', () => {
    const d = new Date(2026, 3, 18, 14, 0); // samedi
    expect(getCurrentTariffPeriod(d).period).toBe('HC');
  });
});

// ══════════════════════════════════════════════════════════════════════════
// Conformité — deriveScoreFromFindings
// ══════════════════════════════════════════════════════════════════════════

describe('deriveScoreFromFindings', () => {
  it('retourne pourcentage ok/(ok+nok)', () => {
    const score = deriveScoreFromFindings({ ok: 2, nok: 1, unknown: 1, out_of_scope: 0 });
    // ok/(ok+nok) = 2/3 = 66.7
    expect(score).toBeCloseTo(66.7, 1);
  });
  it('tous out_of_scope → "not_applicable"', () => {
    const score = deriveScoreFromFindings({ ok: 0, nok: 0, unknown: 0, out_of_scope: 3 });
    expect(score).toBe('not_applicable');
  });
  it('tous unknown → null (en attente)', () => {
    const score = deriveScoreFromFindings({ ok: 0, nok: 0, unknown: 4, out_of_scope: 1 });
    expect(score).toBeNull();
  });
  it('findings vide → null', () => {
    expect(deriveScoreFromFindings(null)).toBeNull();
  });
});

describe('computeScoreDelta', () => {
  it('trend 6 mois → delta entre premier et dernier', () => {
    const trend = [
      { month: '2025-11', score: 42 },
      { month: '2026-04', score: 59.4 },
    ];
    const delta = computeScoreDelta(trend);
    expect(delta.direction).toBe('up');
    expect(delta.text).toMatch(/\+17/);
    expect(delta.text).toMatch(/pts/);
  });
  it('trend trop court → null', () => {
    expect(computeScoreDelta([{ month: '2026-04', score: 50 }])).toBeNull();
    expect(computeScoreDelta([])).toBeNull();
  });
});

// ══════════════════════════════════════════════════════════════════════════
// Achat — interpretEcheance
// ══════════════════════════════════════════════════════════════════════════

describe('interpretEcheance', () => {
  it('< 90 jours → tone=afaire', () => {
    const r = interpretEcheance({ days_until_expiry: 28, supplier_name: 'Eni', site_nom: 'Lyon' });
    expect(r.tone).toBe('afaire');
    expect(r.value).toBe('28');
    expect(r.unit).toContain('jour');
    expect(r.headline).toMatch(/imminent|Eni|Lyon/);
  });
  it('90-180 jours → tone=attention + unit en mois', () => {
    const r = interpretEcheance({ days_until_expiry: 150, supplier_name: 'EDF', site_nom: 'Paris' });
    expect(r.tone).toBe('attention');
    expect(r.unit).toContain('mois');
    expect(r.headline).toMatch(/arbitrage/);
  });
  it('> 180 jours → tone=calme', () => {
    const r = interpretEcheance({ days_until_expiry: 400, supplier_name: 'TotalEnergies' });
    expect(r.tone).toBe('calme');
  });
  it('days négatif → tone=afaire + "dépassés"', () => {
    const r = interpretEcheance({ days_until_expiry: -5, supplier_name: 'X', site_nom: 'Y' });
    expect(r.tone).toBe('afaire');
    expect(r.headline).toMatch(/dépassé|préavis/);
  });
  it('nextRenewal null → headline d\'invitation', () => {
    const r = interpretEcheance(null);
    expect(r.value).toBe('—');
    expect(r.tone).toBe('calme');
  });
});

describe('interpretPrixPondere', () => {
  it('prix > spot 15 %+ → gap narratif', () => {
    const headline = interpretPrixPondere({ weightedPrice: 80, marketSpot: 60 });
    expect(headline).toMatch(/33.*%.*au-dessus|dessus/);
  });
  it('prix < spot 10 %+ → position avantageuse', () => {
    const headline = interpretPrixPondere({ weightedPrice: 50, marketSpot: 60 });
    expect(headline).toMatch(/avantageux|préserver/);
  });
  it('prix null → invitation saisie', () => {
    const headline = interpretPrixPondere({ weightedPrice: null });
    expect(headline).toMatch(/Saisissez|contrats/);
  });
});

describe('estimateWeightedPrice', () => {
  it('retourne spot × 1.2 si sites présents', () => {
    const price = estimateWeightedPrice({
      marketSpot: 60,
      assistantSites: [{ id: 1 }, { id: 2 }],
    });
    expect(price).toBe(72); // 60 × 1.2
  });
  it('retourne null si pas de sites', () => {
    expect(estimateWeightedPrice({ marketSpot: 60, assistantSites: [] })).toBeNull();
    expect(estimateWeightedPrice({ marketSpot: null })).toBeNull();
  });
});

describe('synthesizeMarketTrend', () => {
  it('retourne 12 points avec month + spot', () => {
    const trend = synthesizeMarketTrend({
      spot_avg_12m_eur_mwh: 55,
      spot_current_eur_mwh: 60,
      spot_avg_30d_eur_mwh: 54,
    });
    expect(trend).toHaveLength(12);
    expect(trend[0]).toHaveProperty('month');
    expect(trend[0]).toHaveProperty('spot');
  });
  it('données manquantes → []', () => {
    expect(synthesizeMarketTrend(null)).toEqual([]);
    expect(synthesizeMarketTrend({})).toEqual([]);
  });
});

describe('detectOpportunityArea', () => {
  it('détecte fenêtre spot < userPrice - 3', () => {
    const trend = [
      { month: 'janv.', spot: 70 },
      { month: 'févr.', spot: 50 },
      { month: 'mars', spot: 55 },
      { month: 'avril', spot: 72 },
    ];
    const area = detectOpportunityArea(trend, 65);
    expect(area).not.toBeNull();
    expect(area.label).toMatch(/favorable/i);
  });
  it('pas de fenêtre → null', () => {
    const trend = [{ month: 'janv.', spot: 80 }, { month: 'févr.', spot: 82 }];
    expect(detectOpportunityArea(trend, 65)).toBeNull();
  });
});

// ══════════════════════════════════════════════════════════════════════════
// Patrimoine — EUI
// ══════════════════════════════════════════════════════════════════════════

describe('computeSiteEui', () => {
  it('conso / surface', () => {
    expect(computeSiteEui({ surface_m2: 1000, conso_kwh_an: 150000 })).toBe(150);
  });
  it('surface 0 → null', () => {
    expect(computeSiteEui({ surface_m2: 0, conso_kwh_an: 1000 })).toBeNull();
  });
  it('conso 0 → null (pas 0)', () => {
    expect(computeSiteEui({ surface_m2: 1000, conso_kwh_an: 0 })).toBeNull();
  });
});

describe('computeAvgEui', () => {
  it('moyenne pondérée par surface', () => {
    const sites = [
      { surface_m2: 1000, conso_kwh_an: 200000 }, // EUI 200
      { surface_m2: 2000, conso_kwh_an: 300000 }, // EUI 150
    ];
    // Σconso/Σsurface = 500000 / 3000 = 166.7
    const avg = computeAvgEui(sites);
    expect(avg).toBeCloseTo(166.7, 1);
  });
  it('liste vide → null', () => {
    expect(computeAvgEui([])).toBeNull();
  });
});

describe('computeAvgBenchmark', () => {
  it('pondère par surface selon type ADEME', () => {
    const sites = [
      { surface_m2: 1000, type: 'bureau' }, // benchmark 210
      { surface_m2: 1000, type: 'entrepot' }, // benchmark 80
    ];
    // Σ(bench × surface) / Σsurface = (210000 + 80000) / 2000 = 145
    const avg = computeAvgBenchmark(sites);
    expect(avg).toBe(145);
  });
});

describe('topEuiDrivers', () => {
  it('retourne sites avec gap > 0 trié décroissant', () => {
    const sites = [
      { nom: 'A', type: 'bureau', surface_m2: 1000, conso_kwh_an: 250000 }, // EUI 250 vs 210, gap +19 %
      { nom: 'B', type: 'entrepot', surface_m2: 1000, conso_kwh_an: 120000 }, // EUI 120 vs 80, gap +50 %
      { nom: 'C', type: 'bureau', surface_m2: 1000, conso_kwh_an: 180000 }, // EUI 180 vs 210, gap -14 %
    ];
    const drivers = topEuiDrivers(sites);
    expect(drivers).toHaveLength(2); // C exclu (gap négatif)
    expect(drivers[0].site.nom).toBe('B'); // gap 50 en tête
    expect(drivers[0].gapPct).toBe(50);
  });
});

// ══════════════════════════════════════════════════════════════════════════
// Bill Intelligence
// ══════════════════════════════════════════════════════════════════════════

describe('extractCurrentMonthTotals', () => {
  it('retourne derniers 2 mois disponibles', () => {
    const compare = {
      months: [
        { month: 1, current_eur: 30000 },
        { month: 2, current_eur: 35000 },
        { month: 3, current_eur: 40000 },
        { month: 4, current_eur: null },
      ],
    };
    const r = extractCurrentMonthTotals(compare);
    expect(r.currentEur).toBe(40000);
    expect(r.previousMonthEur).toBe(35000);
  });
  it('vide → null/null', () => {
    expect(extractCurrentMonthTotals(null).currentEur).toBeNull();
  });
});

describe('estimateRecoveredYtd', () => {
  it('somme insights resolved', () => {
    const insights = [
      { insight_status: 'resolved', estimated_loss_eur: 1000 },
      { insight_status: 'open', estimated_loss_eur: 500 },
      { insight_status: 'resolved', estimated_loss_eur: 2500 },
    ];
    expect(estimateRecoveredYtd(insights)).toBe(3500);
  });
});

describe('countContestableAnomalies', () => {
  it('compte types shadow_gap/reseau_mismatch severity high ou critical', () => {
    const insights = [
      { type: 'shadow_gap', severity: 'high' },         // OK
      { type: 'reseau_mismatch', severity: 'critical' }, // OK
      { type: 'reseau_mismatch', severity: 'medium' },  // NON (severity low)
      { type: 'unit_price_high', severity: 'high' },    // NON (type non contestable)
    ];
    expect(countContestableAnomalies(insights)).toBe(2);
  });
});

// ══════════════════════════════════════════════════════════════════════════
// business_errors
// ══════════════════════════════════════════════════════════════════════════

describe('businessErrorFallback', () => {
  it('retourne shape SolWeekCard valide', () => {
    const c = businessErrorFallback('conformite.no_drift');
    expect(c).toHaveProperty('id');
    expect(c).toHaveProperty('tagKind');
    expect(c).toHaveProperty('title');
    expect(c).toHaveProperty('body');
  });
  it('slot désambiguïse l\'id (Phase 4.5 fix)', () => {
    const a = businessErrorFallback('achat.all_stable', 0);
    const b = businessErrorFallback('achat.all_stable', 1);
    expect(a.id).not.toBe(b.id);
  });
  it('clé inconnue → fallback generic', () => {
    const c = businessErrorFallback('clé_inexistante');
    expect(c.title).toBe(BUSINESS_ERRORS['generic.no_data'].title);
  });
});

// ══════════════════════════════════════════════════════════════════════════
// buildFallbackLoadCurve
// ══════════════════════════════════════════════════════════════════════════

describe('buildFallbackLoadCurve', () => {
  it('retourne 24 points avec time + value', () => {
    const curve = buildFallbackLoadCurve();
    expect(curve).toHaveLength(24);
    expect(curve[0]).toHaveProperty('time');
    expect(curve[0]).toHaveProperty('value');
  });
  it('valeurs numériques positives', () => {
    const curve = buildFallbackLoadCurve();
    curve.forEach((pt) => {
      expect(typeof pt.value).toBe('number');
      expect(pt.value).toBeGreaterThan(0);
    });
  });
});

describe('adaptEmsSeriesToLoadCurve', () => {
  it('convertit [{t,v}] → [{time,value}]', () => {
    const raw = [
      { t: '2026-04-19T10:00:00', v: 85.5 },
      { t: '2026-04-19T10:30:00', v: 90 },
    ];
    const adapted = adaptEmsSeriesToLoadCurve(raw);
    expect(adapted).toHaveLength(2);
    expect(adapted[0].time).toMatch(/10:00/);
    expect(adapted[0].value).toBe(86); // arrondi
  });
  it('valeurs null filtrées', () => {
    const raw = [{ t: '2026-04-19T10:00:00', v: null }, { t: 'bad', v: 50 }];
    expect(adaptEmsSeriesToLoadCurve(raw)).toEqual([]);
  });
});
