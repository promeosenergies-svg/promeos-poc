/**
 * M2-5.2 — Tests des constantes UI (environnement node, logique pure).
 */
import { describe, expect, test } from 'vitest';

import {
  COPY,
  LIFECYCLE_BADGE_VARIANTS,
  LIFECYCLE_LABELS,
  LIFECYCLE_ORDER,
  LIFECYCLE_SOL_VARIANTS,
  KIND_LABELS,
  KIND_LABELS_UPPER,
  KIND_SOL_VARIANTS,
  PRIORITY_LABELS,
  PRIORITY_BADGE_VARIANTS,
  PRIORITY_ORDER,
  PRIORITY_SOL_BG,
  DOMAIN_LABELS,
  DOMAIN_SOL_VARIANTS,
  MASTHEAD_COPY,
  SOL_COPY,
} from '../constants';

describe('M2-5.2 constants', () => {
  test('LIFECYCLE_LABELS has the 5 doctrinal states', () => {
    expect(Object.keys(LIFECYCLE_LABELS).sort()).toEqual([
      'closed',
      'in_progress',
      'new',
      'planned',
      'triaged',
    ]);
  });

  test('LIFECYCLE_ORDER respects the chronological order', () => {
    expect(LIFECYCLE_ORDER).toEqual(['new', 'triaged', 'planned', 'in_progress', 'closed']);
  });

  test('LIFECYCLE_BADGE_VARIANTS covers exactly all states', () => {
    expect(Object.keys(LIFECYCLE_BADGE_VARIANTS).sort()).toEqual(
      Object.keys(LIFECYCLE_LABELS).sort()
    );
  });

  test('closed maps to the "ok" Badge status', () => {
    expect(LIFECYCLE_BADGE_VARIANTS.closed).toBe('ok');
  });

  test('in_progress maps to the "warn" Badge status', () => {
    expect(LIFECYCLE_BADGE_VARIANTS.in_progress).toBe('warn');
  });
});

describe('M2-5.8.B constants', () => {
  test('KIND_LABELS covers the 7 backend kind values', () => {
    expect(Object.keys(KIND_LABELS).sort()).toEqual([
      'action',
      'anomaly',
      'deadline',
      'decision',
      'evidence_request',
      'recommendation',
      'signal',
    ]);
  });

  test('PRIORITY_LABELS covers the 4 brackets', () => {
    expect(Object.keys(PRIORITY_LABELS).sort()).toEqual(['P0', 'P1', 'P2', 'P3']);
  });

  test('PRIORITY_BADGE_VARIANTS is aligned with PRIORITY_LABELS', () => {
    expect(Object.keys(PRIORITY_BADGE_VARIANTS).sort()).toEqual(
      Object.keys(PRIORITY_LABELS).sort()
    );
  });

  test('PRIORITY_ORDER goes from most to least urgent', () => {
    expect(PRIORITY_ORDER).toEqual(['P0', 'P1', 'P2', 'P3']);
  });

  test('P0 maps to the "crit" Badge status', () => {
    expect(PRIORITY_BADGE_VARIANTS.P0).toBe('crit');
  });
});

describe('M2-5.9.bis constants', () => {
  test('DOMAIN_LABELS covers the 7 backend Domain values', () => {
    expect(Object.keys(DOMAIN_LABELS).sort()).toEqual([
      'conformite',
      'data_quality',
      'facturation',
      'flexibilite',
      'maintenance',
      'optimisation',
      'purchase',
    ]);
  });

  test('every DOMAIN_LABELS value is a non-empty FR string', () => {
    Object.values(DOMAIN_LABELS).forEach((label) => {
      expect(typeof label).toBe('string');
      expect(label.length).toBeGreaterThan(0);
    });
  });
});

describe('M2-5.10.A — Sol design tokens (fidélité doctrine v0.2)', () => {
  test('KIND_LABELS_UPPER covers the 7 backend kinds', () => {
    expect(Object.keys(KIND_LABELS_UPPER).sort()).toEqual(Object.keys(KIND_LABELS).sort());
  });

  test('KIND_LABELS_UPPER values are all uppercase', () => {
    Object.values(KIND_LABELS_UPPER).forEach((label) => {
      expect(label).toBe(label.toUpperCase());
    });
  });

  test('KIND_SOL_VARIANTS covers exactly the 7 kinds and exposes bg/border/color/borderStyle', () => {
    expect(Object.keys(KIND_SOL_VARIANTS).sort()).toEqual(Object.keys(KIND_LABELS).sort());
    Object.values(KIND_SOL_VARIANTS).forEach((v) => {
      expect(v.bg).toMatch(/var\(--sol-/);
      expect(v.border).toMatch(/var\(--sol-/);
      expect(v.color).toMatch(/var\(--sol-/);
      expect(['solid', 'dashed', 'dotted']).toContain(v.borderStyle);
    });
  });

  test('signal is dashed and recommendation is dotted (signature visuelle doctrinale)', () => {
    expect(KIND_SOL_VARIANTS.signal.borderStyle).toBe('dashed');
    expect(KIND_SOL_VARIANTS.recommendation.borderStyle).toBe('dotted');
  });

  test('LIFECYCLE_SOL_VARIANTS covers exactly the 5 states', () => {
    expect(Object.keys(LIFECYCLE_SOL_VARIANTS).sort()).toEqual(
      Object.keys(LIFECYCLE_LABELS).sort()
    );
  });

  test('DOMAIN_SOL_VARIANTS covers exactly the 7 domains', () => {
    expect(Object.keys(DOMAIN_SOL_VARIANTS).sort()).toEqual(Object.keys(DOMAIN_LABELS).sort());
  });

  test('PRIORITY_SOL_BG covers the 4 brackets with Sol tokens', () => {
    expect(Object.keys(PRIORITY_SOL_BG).sort()).toEqual(['P0', 'P1', 'P2', 'P3']);
    Object.values(PRIORITY_SOL_BG).forEach((c) => expect(c).toMatch(/var\(--sol-/));
  });

  test('MASTHEAD_COPY exposes title + subtitle + dateLive', () => {
    expect(MASTHEAD_COPY.title).toBeTruthy();
    expect(MASTHEAD_COPY.subtitle).toBeTruthy();
    expect(MASTHEAD_COPY.dateLive).toBeTruthy();
  });

  test('SOL_COPY exposes filter labels and reset ARIA', () => {
    expect(SOL_COPY.filterLabelClassement).toBeTruthy();
    expect(SOL_COPY.filterLabelPriorisation).toBeTruthy();
    expect(SOL_COPY.filterAllKinds).toBeTruthy();
    expect(SOL_COPY.filterReset).toBeTruthy();
    expect(typeof SOL_COPY.kindChipAria).toBe('function');
  });
});

describe('M2-5.10.A.bis — hotfix audit findings', () => {
  test('MASTHEAD_COPY.itemsSuffix pluralises FR correctly', () => {
    expect(MASTHEAD_COPY.itemsSuffix(1)).toBe('1 item');
    expect(MASTHEAD_COPY.itemsSuffix(2)).toBe('2 items');
    expect(MASTHEAD_COPY.itemsSuffix(147)).toBe('147 items');
  });

  test('COPY.columnDomain exposes the FR header label (fix code-reviewer P1-2)', () => {
    expect(COPY.columnDomain).toBe('Domaine');
  });

  test('emptyFilteredTitle/Text reformulated for pagination clarity (fix CS P0-2)', () => {
    // L'ancien texte « Aucune action pour ce filtre sur cette page » créait
    // un faux négatif. Le nouveau doit expliciter la pagination et le reset.
    expect(COPY.emptyFilteredTitle).toMatch(/aucun résultat/i);
    expect(COPY.emptyFilteredText).toMatch(/page/i);
    expect(COPY.emptyFilteredText).toMatch(/réinitialiser/i);
  });
});
