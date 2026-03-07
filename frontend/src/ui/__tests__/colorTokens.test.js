/**
 * PROMEOS — Color Tokens Tests
 * Covers: tint helper API, module/severity disambiguation, KPI_ACCENTS, SEVERITY_TINT.
 */
import { describe, it, expect } from 'vitest';
import { KPI_ACCENTS, SEVERITY_TINT, ACCENT_BAR, HERO_ACCENTS, tint } from '../colorTokens';
import { NAV_MODULES, TINT_PALETTE } from '../../layout/NavRegistry';

/* ── tint.module ── */
describe('tint.module', () => {
  it('returns navActive classes for pilotage (blue)', () => {
    const classes = tint.module('pilotage').navActive();
    expect(classes).toContain('bg-blue');
    expect(classes).toContain('text-blue');
    expect(classes).toContain('border-blue');
  });

  it('returns pill classes for achat (amber)', () => {
    const classes = tint.module('achat').pill();
    expect(classes).toContain('bg-amber');
    expect(classes).toContain('text-amber');
    expect(classes).toContain('ring-1');
  });

  it('returns headerBand gradient', () => {
    const hb = tint.module('patrimoine').headerBand();
    expect(hb).toMatch(/^from-emerald/);
    expect(hb).toContain('to-transparent');
  });

  it('returns icon class', () => {
    expect(tint.module('energie').icon()).toBe('text-indigo-500');
  });

  it('falls back to slate for unknown module', () => {
    const classes = tint.module('unknown').icon();
    expect(classes).toContain('slate');
  });

  it('raw() returns full TINT_PALETTE entry', () => {
    const raw = tint.module('pilotage').raw();
    expect(raw).toBe(TINT_PALETTE.blue);
  });

  it('covers all 5 modules without error', () => {
    for (const mod of NAV_MODULES) {
      expect(() => tint.module(mod.key).navActive()).not.toThrow();
      expect(() => tint.module(mod.key).pill()).not.toThrow();
      expect(() => tint.module(mod.key).icon()).not.toThrow();
    }
  });
});

/* ── tint.severity ── */
describe('tint.severity', () => {
  it('returns badge classes for critical (red)', () => {
    const classes = tint.severity('critical').badge();
    expect(classes).toContain('bg-red');
    expect(classes).toContain('text-red');
    expect(classes).toContain('border');
  });

  it('returns dot class for high', () => {
    expect(tint.severity('high').dot()).toBe('bg-amber-500');
  });

  it('returns FR label for critical', () => {
    expect(tint.severity('critical').label()).toBe('Critique');
  });

  it('returns FR label for warn', () => {
    expect(tint.severity('warn').label()).toBe('Attention');
  });

  it('falls back to neutral for unknown level', () => {
    const classes = tint.severity('nonexistent').badge();
    expect(classes).toContain('gray');
  });

  it('covers all 7 severity levels', () => {
    const levels = ['critical', 'high', 'warn', 'medium', 'info', 'low', 'neutral'];
    for (const level of levels) {
      expect(() => tint.severity(level).badge()).not.toThrow();
      expect(tint.severity(level).label()).toBeTruthy();
    }
  });
});

/* ── tint.module — tab recipe ── */
describe('tint.module — tab recipe', () => {
  it('returns tab object with active and ring', () => {
    const tab = tint.module('pilotage').tab();
    expect(tab).toHaveProperty('active');
    expect(tab).toHaveProperty('ring');
    expect(tab.active).toContain('border-b-2');
    expect(tab.active).toContain('text-blue');
  });

  it('achat tab uses amber', () => {
    const tab = tint.module('achat').tab();
    expect(tab.active).toContain('amber');
  });

  it('covers all 5 modules without error', () => {
    for (const mod of NAV_MODULES) {
      const tab = tint.module(mod.key).tab();
      expect(tab.active).toBeTruthy();
      expect(tab.ring).toBeTruthy();
    }
  });
});

/* ── Module vs Severity Disambiguation ── */
describe('module vs severity disambiguation', () => {
  it('module amber pill differs from severity amber badge', () => {
    const moduleAmber = tint.module('achat').pill();
    const severityAmber = tint.severity('high').badge();
    expect(moduleAmber).not.toBe(severityAmber);
  });

  it('module tint keys (pilotage..admin) do not overlap severity keys (critical..neutral)', () => {
    const moduleKeys = new Set(NAV_MODULES.map((m) => m.key));
    const severityKeys = new Set(Object.keys(SEVERITY_TINT));
    for (const k of moduleKeys) {
      expect(severityKeys.has(k)).toBe(false);
    }
  });

  it('every module has exactly one tint key in TINT_PALETTE', () => {
    for (const mod of NAV_MODULES) {
      expect(TINT_PALETTE).toHaveProperty(mod.tint);
    }
  });

  it('module amber softBg differs from severity warn chipBg', () => {
    const moduleAmber = tint.module('achat').softBg();
    const severityWarn = tint.severity('warn').raw().chipBg;
    expect(moduleAmber).not.toBe(severityWarn);
  });
});

/* ── KPI_ACCENTS ── */
describe('KPI_ACCENTS', () => {
  it('has 6 accent profiles', () => {
    expect(Object.keys(KPI_ACCENTS)).toHaveLength(6);
  });

  it('each profile has required keys', () => {
    for (const [, cfg] of Object.entries(KPI_ACCENTS)) {
      expect(cfg).toHaveProperty('accent');
      expect(cfg).toHaveProperty('iconBg');
      expect(cfg).toHaveProperty('iconText');
      expect(cfg).toHaveProperty('border');
    }
  });
});

/* ── ACCENT_BAR ── */
describe('ACCENT_BAR', () => {
  it('has 4 color entries', () => {
    expect(Object.keys(ACCENT_BAR)).toHaveLength(4);
  });

  it('each is a bg- class', () => {
    for (const val of Object.values(ACCENT_BAR)) {
      expect(val).toMatch(/^bg-/);
    }
  });
});

/* ── HERO_ACCENTS ── */
describe('HERO_ACCENTS', () => {
  it('has priority, success, executive', () => {
    expect(HERO_ACCENTS).toHaveProperty('priority');
    expect(HERO_ACCENTS).toHaveProperty('success');
    expect(HERO_ACCENTS).toHaveProperty('executive');
  });
});
