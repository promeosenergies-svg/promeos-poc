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

// ══════════════════════════════════════════════════════════════════════════
// Site360Sol presenters (Lot 3 Phase 2)
// ══════════════════════════════════════════════════════════════════════════

import * as SitePresenters from '../sites/sol_presenters';

describe('Site360Sol · normalizeCompliance', () => {
  it('retourne null pour input null/undefined', () => {
    expect(SitePresenters.normalizeCompliance(null)).toBe(null);
    expect(SitePresenters.normalizeCompliance(undefined)).toBe(null);
  });

  it('arrondit score et mappe breakdown tertiaire_operat → dt', () => {
    const raw = {
      score: 62.4,
      breakdown: [
        { framework: 'tertiaire_operat', score: 58.7 },
        { framework: 'bacs', score: 80 },
      ],
    };
    const out = SitePresenters.normalizeCompliance(raw);
    expect(out.overall).toBe(62);
    expect(out.breakdown.dt).toBe(59);
    expect(out.breakdown.bacs).toBe(80);
    expect(out.breakdown.aper).toBeUndefined();
  });

  it('accepte shape déjà normalisée (overall + breakdown object)', () => {
    const raw = { overall: 80, breakdown: [], baseline: 45 };
    const out = SitePresenters.normalizeCompliance(raw);
    expect(out.overall).toBe(80);
    expect(out.baseline).toBe(45);
  });
});

describe('Site360Sol · buildSiteKicker', () => {
  it('uppercase type + ville', () => {
    const k = SitePresenters.buildSiteKicker({ usage: 'bureau', ville: 'Lyon' });
    expect(k).toBe('SITE · BUREAUX · LYON');
  });
  it('sans ville : pas de séparateur vide', () => {
    const k = SitePresenters.buildSiteKicker({ usage: 'entrepot' });
    expect(k).toBe('SITE · ENTREPÔT');
  });
  it('fallback site null', () => {
    expect(SitePresenters.buildSiteKicker(null)).toBe('SITE');
  });
});

describe('Site360Sol · statusPillFromSite', () => {
  it('score >= 75 → calme Conforme', () => {
    const p = SitePresenters.statusPillFromSite({ compliance: { overall: 82 } });
    expect(p.tone).toBe('calme');
    expect(p.label).toBe('Conforme');
  });
  it('score 60-74 → attention À surveiller', () => {
    const p = SitePresenters.statusPillFromSite({ compliance: { overall: 68 } });
    expect(p.tone).toBe('attention');
  });
  it('score < 60 → afaire À traiter', () => {
    const p = SitePresenters.statusPillFromSite({ compliance: { overall: 50 } });
    expect(p.tone).toBe('afaire');
  });
  it('fallback statut_conformite si pas de score', () => {
    const p = SitePresenters.statusPillFromSite({
      site: { statut_conformite: 'non_conforme' },
    });
    expect(p.tone).toBe('afaire');
  });
  it('null si aucun signal', () => {
    expect(SitePresenters.statusPillFromSite({ site: {} })).toBe(null);
  });
});

describe('Site360Sol · buildEntityCardFields', () => {
  it('PDL depuis deliveryPoints, fallback "—" si absent', () => {
    const site = { siret: '12345678901234', surface_m2: 3240, usage: 'bureau' };
    const dps = [{ prm: '14511234567890' }];
    const fields = SitePresenters.buildEntityCardFields({ site, deliveryPoints: dps });
    const pdl = fields.find((f) => f.label === 'PDL / PRM');
    expect(pdl.value).toBe('14511234567890');
    expect(pdl.mono).toBe(true);
  });

  it('conso affichée en MWh si > 0, absente sinon', () => {
    const withConso = SitePresenters.buildEntityCardFields({
      site: { conso_kwh_an: 412000, usage: 'bureau' },
      deliveryPoints: [],
    });
    expect(withConso.find((f) => f.label === 'Conso 12 mois')).toBeDefined();

    const noConso = SitePresenters.buildEntityCardFields({
      site: { usage: 'bureau' },
      deliveryPoints: [],
    });
    expect(noConso.find((f) => f.label === 'Conso 12 mois')).toBeUndefined();
  });
});

describe('Site360Sol · interpretSiteEui', () => {
  it('fallback narratif si pas de data intensité', () => {
    const r = SitePresenters.interpretSiteEui({ intensityData: { hasIntensity: false } });
    expect(r).toMatch(/indisponible/i);
  });

  it('> 10 % au-dessus : annonce gap', () => {
    const r = SitePresenters.interpretSiteEui({
      intensityData: { hasIntensity: true, intensity: 150, benchmark: 100 },
      site: { usage: 'bureau' },
    });
    expect(r).toMatch(/50/);
    expect(r).toMatch(/au-dessus/);
  });

  it('< -5 % : annonce "mieux que"', () => {
    const r = SitePresenters.interpretSiteEui({
      intensityData: { hasIntensity: true, intensity: 85, benchmark: 100 },
      site: { usage: 'bureau' },
    });
    expect(r).toMatch(/mieux/i);
  });

  it('aligned : phrase neutre', () => {
    const r = SitePresenters.interpretSiteEui({
      intensityData: { hasIntensity: true, intensity: 102, benchmark: 100 },
      site: { usage: 'bureau' },
    });
    expect(r).toMatch(/[aA]ligné/);
  });
});

describe('Site360Sol · buildSiteWeekCards', () => {
  it('3 cards : anomalie + reco + compliance si tout dispo', () => {
    const cards = SitePresenters.buildSiteWeekCards({
      site: { id: 7, compliance_score: 82 },
      anomalies: [{ id: 'a1', title: 'CTA incorrecte', impact_eur: 1847 }],
      topReco: { id: 'r1', title: 'Reprogrammation HC', impact_eur: 3000 },
      compliance: { overall: 82 },
    });
    expect(cards).toHaveLength(3);
    expect(cards[0].tagKind).toBe('attention');
    expect(cards[1].tagKind).toBe('afaire');
    expect(cards[2].tagKind).toBe('succes');
  });

  it('fallbacks business_errors si data absente', () => {
    const cards = SitePresenters.buildSiteWeekCards({
      site: { id: 7 },
      anomalies: [],
      topReco: null,
      compliance: null,
    });
    expect(cards).toHaveLength(3);
    expect(cards[0].id).toContain('site.no_anomalies');
    expect(cards[1].id).toContain('site.no_reco');
  });

  it('anomalies resolved_at exclues du tri', () => {
    const cards = SitePresenters.buildSiteWeekCards({
      site: { id: 7 },
      anomalies: [{ id: 'a1', resolved_at: '2026-03-01', title: 'Old' }],
      topReco: null,
      compliance: null,
    });
    expect(cards[0].id).toContain('site.no_anomalies');
  });
});

describe('Site360Sol · adaptComplianceToTrajectory', () => {
  it('null si aucun score', () => {
    expect(
      SitePresenters.adaptComplianceToTrajectory({ site: {}, compliance: null })
    ).toBe(null);
  });

  it('3 points 2020/2024/2030 avec score cible 75', () => {
    const data = SitePresenters.adaptComplianceToTrajectory({
      site: { compliance_score: 62 },
      compliance: null,
    });
    expect(data).toHaveLength(3);
    expect(data[0].month).toBe('2020');
    expect(data[2].score).toBe(75);
    expect(data[1].score).toBe(62);
  });
});

describe('Site360Sol · labelUsage', () => {
  it('aliases bureau/bureaux → bureaux', () => {
    expect(SitePresenters.labelUsage('bureau')).toBe('bureaux');
    expect(SitePresenters.labelUsage('bureaux')).toBe('bureaux');
  });
  it('fallback générique pour inconnu', () => {
    expect(SitePresenters.labelUsage(null)).toBe('tertiaire');
    expect(SitePresenters.labelUsage('unknown_type')).toBe('unknown_type');
  });
});

// ══════════════════════════════════════════════════════════════════════════
// RegOpsSol presenters (Lot 3 Phase 3)
// ══════════════════════════════════════════════════════════════════════════

import * as RegOpsPresenters from '../regops/sol_presenters';

describe('RegOpsSol · normalizeAssessment', () => {
  it('retourne null pour input null', () => {
    expect(RegOpsPresenters.normalizeAssessment(null)).toBe(null);
  });
  it('fallback global_status UNKNOWN si absent', () => {
    const out = RegOpsPresenters.normalizeAssessment({ site_id: 3 });
    expect(out.global_status).toBe('UNKNOWN');
    expect(out.findings).toEqual([]);
    expect(out.actions).toEqual([]);
    expect(out.missing_data).toEqual([]);
  });
  it('préserve findings + actions + missing_data si arrays', () => {
    const out = RegOpsPresenters.normalizeAssessment({
      site_id: 3,
      compliance_score: 67,
      global_status: 'AT_RISK',
      findings: [{ rule_id: 'dt_2030' }],
      actions: [{ label: 'Déposer' }],
      missing_data: ['surface_m2'],
    });
    expect(out.compliance_score).toBe(67);
    expect(out.findings).toHaveLength(1);
    expect(out.actions).toHaveLength(1);
    expect(out.missing_data).toHaveLength(1);
  });
});

describe('RegOpsSol · computeCompletion', () => {
  it('retourne null si pas d\'obligation applicable', () => {
    expect(RegOpsPresenters.computeCompletion([])).toEqual({
      percent: null,
      compliant: 0,
      total: 0,
    });
  });
  it('exclut la catégorie incentive (CEE masqué V1.2)', () => {
    const r = RegOpsPresenters.computeCompletion([
      { status: 'COMPLIANT', category: 'obligation' },
      { status: 'COMPLIANT', category: 'incentive' },
      { status: 'NON_COMPLIANT', category: 'obligation' },
    ]);
    expect(r.total).toBe(2);
    expect(r.compliant).toBe(1);
    expect(r.percent).toBe(50);
  });
  it('arrondit le pourcentage au plus proche entier', () => {
    const r = RegOpsPresenters.computeCompletion([
      { status: 'COMPLIANT' },
      { status: 'COMPLIANT' },
      { status: 'NON_COMPLIANT' },
    ]);
    expect(r.percent).toBe(67);
  });
});

describe('RegOpsSol · sumPenalties', () => {
  it('somme uniquement AT_RISK + NON_COMPLIANT', () => {
    const total = RegOpsPresenters.sumPenalties([
      { status: 'COMPLIANT', estimated_penalty_eur: 1000 }, // ignoré
      { status: 'AT_RISK', estimated_penalty_eur: 2000 },
      { status: 'NON_COMPLIANT', estimated_penalty_eur: 3000 },
      { status: 'UNKNOWN', estimated_penalty_eur: 500 }, // ignoré
    ]);
    expect(total).toBe(5000);
  });
  it('0 si aucun finding à risque', () => {
    expect(RegOpsPresenters.sumPenalties([{ status: 'COMPLIANT' }])).toBe(0);
  });
});

describe('RegOpsSol · daysUntil', () => {
  it('null si date invalide ou absente', () => {
    expect(RegOpsPresenters.daysUntil(null)).toBe(null);
    expect(RegOpsPresenters.daysUntil('not-a-date')).toBe(null);
  });
  it('positif pour date future', () => {
    const future = new Date(Date.now() + 10 * 24 * 3600 * 1000).toISOString();
    expect(RegOpsPresenters.daysUntil(future)).toBeGreaterThanOrEqual(9);
    expect(RegOpsPresenters.daysUntil(future)).toBeLessThanOrEqual(10);
  });
  it('négatif pour date passée', () => {
    const past = new Date(Date.now() - 5 * 24 * 3600 * 1000).toISOString();
    expect(RegOpsPresenters.daysUntil(past)).toBeLessThan(0);
  });
});

describe('RegOpsSol · interpretRegOpsDeadline', () => {
  it('null date → phrase neutre', () => {
    expect(RegOpsPresenters.interpretRegOpsDeadline(null)).toMatch(/aucune/i);
  });
  it('< 30 jours → "imminente"', () => {
    const d = new Date(Date.now() + 10 * 24 * 3600 * 1000).toISOString();
    expect(RegOpsPresenters.interpretRegOpsDeadline(d)).toMatch(/imminente/i);
  });
  it('< 90 jours → "fenêtre confortable"', () => {
    const d = new Date(Date.now() + 60 * 24 * 3600 * 1000).toISOString();
    expect(RegOpsPresenters.interpretRegOpsDeadline(d)).toMatch(/confortable/i);
  });
  it('> 90 jours → "lointaine"', () => {
    const d = new Date(Date.now() + 200 * 24 * 3600 * 1000).toISOString();
    expect(RegOpsPresenters.interpretRegOpsDeadline(d)).toMatch(/lointaine/i);
  });
  it('date passée → "dépassée"', () => {
    const d = new Date(Date.now() - 5 * 24 * 3600 * 1000).toISOString();
    expect(RegOpsPresenters.interpretRegOpsDeadline(d)).toMatch(/dépassée/i);
  });
});

describe('RegOpsSol · toneFromSeverity', () => {
  it('CRITICAL → refuse', () => {
    expect(RegOpsPresenters.toneFromSeverity('CRITICAL')).toBe('refuse');
  });
  it('HIGH → attention', () => {
    expect(RegOpsPresenters.toneFromSeverity('HIGH')).toBe('attention');
  });
  it('LOW → succes', () => {
    expect(RegOpsPresenters.toneFromSeverity('LOW')).toBe('succes');
  });
  it('inconnu → afaire par défaut', () => {
    expect(RegOpsPresenters.toneFromSeverity('??')).toBe('afaire');
  });
});

describe('RegOpsSol · statusPillFromAssessment', () => {
  it('COMPLIANT → calme ou succes + label Conforme', () => {
    const p = RegOpsPresenters.statusPillFromAssessment({
      assessment: { global_status: 'COMPLIANT' },
    });
    expect(p.label).toBe('Conforme');
    expect(p.tone).toBe('succes');
  });
  it('NON_COMPLIANT → refuse + Non conforme', () => {
    const p = RegOpsPresenters.statusPillFromAssessment({
      assessment: { global_status: 'NON_COMPLIANT' },
    });
    expect(p.tone).toBe('refuse');
  });
  it('null assessment → null', () => {
    expect(RegOpsPresenters.statusPillFromAssessment({})).toBe(null);
  });
});

describe('RegOpsSol · buildRegOpsTimelineEvents', () => {
  it('tri deadlines ASC puis findings sans deadline par severity', () => {
    const events = RegOpsPresenters.buildRegOpsTimelineEvents({
      assessment: null,
      findings: [
        { rule_id: 'a', regulation: 'bacs', severity: 'LOW', legal_deadline: '2027-01-01' },
        { rule_id: 'b', regulation: 'bacs', severity: 'CRITICAL' }, // sans deadline, severity HIGH → après
        { rule_id: 'c', regulation: 'bacs', severity: 'MEDIUM', legal_deadline: '2026-06-01' },
      ],
    });
    expect(events).toHaveLength(3);
    expect(events[0].id).toContain('c'); // deadline la plus proche
    expect(events[1].id).toContain('a');
    expect(events[2].id).toContain('b'); // sans deadline
  });
  it('ajoute jalon next_deadline global si absent des findings', () => {
    const future = new Date(Date.now() + 45 * 24 * 3600 * 1000).toISOString();
    const events = RegOpsPresenters.buildRegOpsTimelineEvents({
      assessment: { next_deadline: future },
      findings: [],
    });
    expect(events).toHaveLength(1);
    expect(events[0].id).toBe('next-deadline');
  });
  it('ignore la catégorie incentive', () => {
    const events = RegOpsPresenters.buildRegOpsTimelineEvents({
      assessment: null,
      findings: [
        { rule_id: 'cee', regulation: 'cee', severity: 'MEDIUM', category: 'incentive' },
      ],
    });
    expect(events).toHaveLength(0);
  });
});

describe('RegOpsSol · buildRegOpsWeekCards (variété tags D1)', () => {
  it('3 cards avec tags distincts (attention + afaire + succes) si data riche', () => {
    const cards = RegOpsPresenters.buildRegOpsWeekCards({
      assessment: {
        actions: [{ label: 'Dépôt OPERAT', priority_score: 85 }],
        missing_data: ['surface_m2', 'année'],
      },
      findings: [
        { rule_id: 'a', regulation: 'bacs', severity: 'CRITICAL', status: 'NON_COMPLIANT' },
        { rule_id: 'b', regulation: 'aper', severity: 'LOW', status: 'COMPLIANT' },
      ],
    });
    expect(cards).toHaveLength(3);
    const tags = cards.map((c) => c.tagKind);
    expect(tags).toContain('attention');
    expect(tags).toContain('afaire');
    expect(tags).toContain('succes');
  });

  it('card 1 critical finding pris avant top action', () => {
    const cards = RegOpsPresenters.buildRegOpsWeekCards({
      assessment: { actions: [{ label: 'X', priority_score: 80 }] },
      findings: [{ rule_id: 'crit', regulation: 'bacs', severity: 'CRITICAL', status: 'NON_COMPLIANT' }],
    });
    expect(cards[0].id).toContain('critical');
  });

  it('card 3 succes fallback "surveillance active" si aucun finding COMPLIANT', () => {
    const cards = RegOpsPresenters.buildRegOpsWeekCards({
      assessment: { actions: [], missing_data: [] },
      findings: [],
    });
    expect(cards[2].tagKind).toBe('succes');
    expect(cards[2].title).toMatch(/surveillance|évaluation/i);
  });

  it('fallback regops.no_findings si aucune action et aucun finding critique', () => {
    const cards = RegOpsPresenters.buildRegOpsWeekCards({
      assessment: { actions: [], missing_data: [] },
      findings: [],
    });
    expect(cards[0].title).toMatch(/aucun finding/i);
  });
});

describe('RegOpsSol · buildRegOpsEntityCardFields', () => {
  it('6 fields dont Site + Obligations + Score + Échéance + Statut OPERAT + Moteur', () => {
    const fields = RegOpsPresenters.buildRegOpsEntityCardFields({
      assessment: {
        site_id: 3,
        compliance_score: 72,
        next_deadline: '2026-09-30',
        deterministic_version: '2.1.0',
      },
      site: { nom: 'Entrepôt Toulouse' },
      findings: [
        { regulation: 'decret_tertiaire_operat', status: 'AT_RISK' },
        { regulation: 'bacs', status: 'COMPLIANT' },
      ],
    });
    expect(fields).toHaveLength(6);
    const labels = fields.map((f) => f.label);
    expect(labels).toContain('Site');
    expect(labels).toContain('Obligations');
    expect(labels).toContain('Score conformité');
    expect(labels).toContain('Prochaine échéance');
    expect(labels).toContain('Statut OPERAT');
    expect(labels).toContain('Moteur');
  });

  it('statut OPERAT "Non applicable" si pas de finding decret_tertiaire_operat', () => {
    const fields = RegOpsPresenters.buildRegOpsEntityCardFields({
      assessment: { site_id: 3, next_deadline: null },
      site: null,
      findings: [{ regulation: 'bacs', status: 'COMPLIANT' }],
    });
    const operat = fields.find((f) => f.label === 'Statut OPERAT');
    expect(operat.value).toBe('Non applicable');
  });
});
