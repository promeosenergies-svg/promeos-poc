/**
 * PROMEOS — Tests FindingCard (Sprint CX 2 item B)
 * Source-guard style (convention projet) : vérifie la structure du composant
 * sans instancier React Testing Library.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join } from 'path';

const SRC = join(__dirname, '..');
const readSrc = (rel) => readFileSync(join(SRC, rel), 'utf-8');

// ── A. Export + structure de base ─────────────────────────────────────────

describe('A. FindingCard — structure', () => {
  const src = readSrc('ui/FindingCard.jsx');

  it('exporte un composant React par défaut', () => {
    expect(src).toMatch(/export default function FindingCard/);
  });

  it('est réexporté depuis ui/index.js', () => {
    const idx = readSrc('ui/index.js');
    expect(idx).toContain("export { default as FindingCard } from './FindingCard'");
  });

  it('utilise des props standardisés (JSDoc)', () => {
    for (const prop of [
      'severity',
      'priority',
      'category',
      'title',
      'description',
      'impact',
      'deadline',
      'confidence',
      'actionLabel',
      'onAction',
      'onClick',
    ]) {
      expect(src).toContain(`props.${prop}`);
    }
  });
});

// ── B. Severity system ────────────────────────────────────────────────────

describe('B. FindingCard — severity', () => {
  const src = readSrc('ui/FindingCard.jsx');

  it('déclare SEVERITY_CONFIG avec 4 niveaux', () => {
    expect(src).toMatch(/SEVERITY_CONFIG\s*=\s*\{/);
    for (const level of ['critical', 'high', 'medium', 'low']) {
      expect(src).toContain(`${level}:`);
    }
  });

  it('chaque niveau a bg, border, dot, text, label', () => {
    for (const field of ['bg:', 'border:', 'dot:', 'text:', 'label:']) {
      // Au moins 4 occurrences (1 par niveau)
      const matches = src.match(new RegExp(field, 'g')) || [];
      expect(matches.length).toBeGreaterThanOrEqual(4);
    }
  });

  it('labels FR pour les 4 niveaux', () => {
    expect(src).toContain("label: 'Critique'");
    expect(src).toContain("label: 'Élevée'");
    expect(src).toContain("label: 'Moyenne'");
    expect(src).toContain("label: 'Info'");
  });

  it('default severity = medium', () => {
    expect(src).toMatch(/severity\s*=\s*['"]medium['"]/);
  });
});

// ── C. Category icons (7 categories cibles) ────────────────────────────────

describe('C. FindingCard — categories', () => {
  const src = readSrc('ui/FindingCard.jsx');

  it('déclare CATEGORY_ICONS map', () => {
    expect(src).toMatch(/CATEGORY_ICONS\s*=\s*\{/);
  });

  it.each(['compliance', 'billing', 'consumption', 'purchase', 'flex', 'audit', 'insight'])(
    'supporte category="%s"',
    (cat) => {
      expect(src).toContain(`${cat}:`);
    }
  );
});

// ── D. data-testid pour tests E2E ──────────────────────────────────────────

describe('D. FindingCard — data-testid hooks', () => {
  const src = readSrc('ui/FindingCard.jsx');

  it.each([
    'finding-card',
    'finding-priority',
    'finding-impact',
    'finding-deadline',
    'finding-confidence',
    'finding-severity-dot',
    'finding-action',
  ])('expose data-testid="%s"', (testid) => {
    expect(src).toContain(`data-testid="${testid}"`);
  });

  it('expose data-severity et data-category pour ciblage', () => {
    expect(src).toContain('data-severity=');
    expect(src).toContain('data-category=');
  });
});

// ── E. Interactivity (a11y) ────────────────────────────────────────────────

describe('E. FindingCard — a11y & interactivity', () => {
  const src = readSrc('ui/FindingCard.jsx');

  it('utilise <button> quand onClick est fourni', () => {
    expect(src).toMatch(
      /Wrapper\s*=\s*typeof\s*onClick\s*===\s*['"]function['"]\s*\?\s*['"]button['"]/
    );
  });

  it('stopPropagation sur le clic du CTA action', () => {
    expect(src).toContain('e.stopPropagation()');
  });

  it('dot severity a aria-label dynamique', () => {
    expect(src).toContain('aria-label={`Sévérité ${cfg.label}`}');
  });

  it('icônes décoratives sont aria-hidden', () => {
    const ariaHiddenCount = (src.match(/aria-hidden="true"/g) || []).length;
    expect(ariaHiddenCount).toBeGreaterThanOrEqual(1);
  });

  it('focus ring sur card interactive', () => {
    expect(src).toContain('focus:ring-');
  });
});

// ── H. Fixes post-code-review ──────────────────────────────────────────────

describe('H. FindingCard — fixes post-code-review PR #228', () => {
  const src = readSrc('ui/FindingCard.jsx');

  it('Sprint CX 2.5-bis F5 : daysUntil sans useMemo (évite staleness à minuit)', () => {
    // useMemo retiré car daysUntil() fait new Date() et la memo ne se rerun pas
    // à minuit → "J-1" restait figé. Calcul trivial donc recompute à chaque render.
    expect(src).not.toContain('import { useMemo }');
    expect(src).not.toMatch(/useMemo\(\(\)\s*=>\s*daysUntil\(deadline\)/);
    expect(src).toMatch(/const\s+days\s*=\s*daysUntil\(deadline\)/);
  });

  it('Fix #2 : dev warning si impact fourni mais tous champs vides', () => {
    expect(src).toContain('import.meta.env?.DEV');
    expect(src).toContain('console.warn');
    expect(src).toContain('impact fourni mais tous champs vides');
  });

  it('Fix #4 : data-category undefined si non fourni (pas de "generic" fallback)', () => {
    expect(src).toContain('data-category={category || undefined}');
    expect(src).not.toContain("data-category={category || 'generic'}");
  });

  it('Sprint CX 2.5-bis F6 : daysUntil parse date-only en local TZ (pas UTC)', () => {
    // Fix timezone bug : new Date('2026-04-20') = UTC midnight, à Paris 1h du matin
    // la soustraction avec now local donnait négatif → "Dépassé" affiché à tort.
    // Fix : split('T')[0] + new Date(y, m-1, d) pour local midnight.
    expect(src).toContain("split('T')[0]");
    expect(src).toMatch(/new Date\(y,\s*m\s*-\s*1,\s*d\)/);
  });
});

// ── F. Impact display unifié ───────────────────────────────────────────────

describe('F. FindingCard — impact (EUR/kWh/CO₂)', () => {
  const src = readSrc('ui/FindingCard.jsx');

  it('supporte eur, kwh, co2e_kg dans impact (F4 : unité ADEME co2e)', () => {
    expect(src).toContain('eur');
    expect(src).toContain('kwh');
    expect(src).toContain('co2e_kg');
    // Sprint CX 2.5-bis F4 : l'ancien nom co2_kg ne doit plus apparaître
    expect(src).not.toMatch(/\bco2_kg\b/);
  });

  it("affiche l'unité kgCO₂e/an (équivalent carbone ADEME)", () => {
    expect(src).toContain('kgCO₂e/an');
  });

  it('utilise fmtEur pour formatage EUR (localisation FR)', () => {
    expect(src).toContain("import { fmtEur } from '../utils/format'");
    expect(src).toContain('fmtEur(eur)');
  });

  it("n'affiche pas ImpactRow si impact est null/absent", () => {
    expect(src).toMatch(/if\s*\(\s*!impact\s*\)\s*return\s*null/);
  });

  it('convertit en français avec toLocaleString("fr-FR")', () => {
    expect(src).toContain("toLocaleString('fr-FR')");
  });
});

// ── G. Deadline badges ─────────────────────────────────────────────────────

describe('G. FindingCard — deadline badges', () => {
  const src = readSrc('ui/FindingCard.jsx');

  it('gère "Dépassé" quand days <= 0', () => {
    expect(src).toContain("'Dépassé'");
  });

  it('gère format "J-X" pour jours futurs', () => {
    expect(src).toContain('J-${days}');
  });

  it('3 seuils de couleur (≤30, ≤90, >90)', () => {
    expect(src).toContain('days <= 30');
    expect(src).toContain('days <= 90');
  });
});
