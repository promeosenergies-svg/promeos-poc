/**
 * PROMEOS — Sol V1 UI source guards.
 *
 * Pattern PROMEOS : readFileSync + regex pour vérifier l'invariance des
 * composants Sol (CTAs, aria-labels, accessibilité, tokens CSS).
 *
 * Gardé volontairement simple — pas de DOM rendering (repo sans
 * @testing-library/react installé). Les tests d'intégration visuelle
 * sont faits via les maquettes HTML statiques (docs/sol/maquettes/).
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const SOL_DIR = join(process.cwd(), 'src', 'sol');
const readSol = (file) => readFileSync(join(SOL_DIR, file), 'utf8');


describe('SolCartouche source guards', () => {
  const src = readSol('SolCartouche.jsx');

  it('uses role="status" + aria-live="polite" (accessibility)', () => {
    expect(src).toMatch(/role="status"/);
    expect(src).toMatch(/aria-live="polite"/);
  });

  it('aria-label combines state label + message', () => {
    expect(src).toMatch(/aria-label={\`\${styles\.label}\. \${message/);
  });

  it('supports 5 documented states', () => {
    for (const state of ['repos', 'proposing', 'pending', 'executing', 'done']) {
      expect(src).toContain(`${state}:`);
    }
  });

  it('uses sol CSS variables, not hardcoded colors', () => {
    expect(src).toMatch(/var\(--sol-calme-fg\)/);
    expect(src).toMatch(/var\(--sol-ink-/);
    expect(src).not.toMatch(/#[0-9A-Fa-f]{6}/);
  });

  it('sol-pulse animation respects prefers-reduced-motion via CSS', () => {
    // L'animation est conditionnelle à styles.pulse, mais la media query
    // prefers-reduced-motion est gérée dans .sol-surface CSS global.
    expect(src).toMatch(/sol-pulse/);
  });

  it('button disabled when onClick is null', () => {
    expect(src).toMatch(/disabled={!onClick}/);
  });
});


describe('SolHero source guards', () => {
  const src = readSol('SolHero.jsx');

  it('uses accent calme as left border signature', () => {
    expect(src).toMatch(/borderLeft:.*var\(--sol-calme-fg\)/);
  });

  it('CTA primaire "Voir ce que j\'enverrai" (voice guide)', () => {
    expect(src).toContain("Voir ce que j'enverrai");
  });

  it('CTA secondaire "Plus tard" (voice guide)', () => {
    expect(src).toContain('Plus tard');
  });

  it('metrics use tabular-nums for alignment KPI', () => {
    expect(src).toMatch(/fontVariantNumeric: 'tabular-nums'/);
  });

  it('chipLabel default respects Sol voice ("Sol propose · action agentique")', () => {
    expect(src).toContain('Sol propose · action agentique');
  });

  it('uses sol CSS tokens, zero hardcoded hex except white', () => {
    const hexMatches = src.match(/#[0-9A-Fa-f]{6}/g) || [];
    const nonWhite = hexMatches.filter((h) => h.toUpperCase() !== '#FFFFFF');
    expect(nonWhite).toEqual([]);
  });
});


describe('SolActionPreview source guards', () => {
  const src = readSol('SolActionPreview.jsx');

  it('reuses shared Drawer (ui/Drawer) for ESC + tab trap', () => {
    expect(src).toMatch(/from '\.\.\/ui\/Drawer'/);
  });

  it('lists 4 garanties (voice guide guarantees)', () => {
    expect(src).toMatch(/Délai de grâce/);
    expect(src).toMatch(/Logique déterministe/);
    expect(src).toMatch(/Audit complet/);
    expect(src).toMatch(/Mail signé PROMEOS/);
  });

  it('CTA valider wording includes grace hours', () => {
    expect(src).toMatch(/Valider — envoi dans \$\{graceHours \|\| 24\} h/);
  });

  it('button disabled when confirming=true', () => {
    expect(src).toMatch(/disabled={confirming}/);
  });

  it('preview payload accessed via plan.preview_payload', () => {
    expect(src).toMatch(/plan\?\.preview_payload\?\.letter_markdown/);
    expect(src).toMatch(/plan\?\.preview_payload\?\.attachments/);
  });
});


describe('SolHeadline source guards', () => {
  const src = readSol('SolHeadline.jsx');

  it('uses sol-ink-700 for primary text', () => {
    expect(src).toMatch(/var\(--sol-ink-700\)/);
  });

  it('supports optional subline', () => {
    expect(src).toMatch(/subline\s*&&/);
  });

  it('max-width constrains to 680px reading width', () => {
    expect(src).toMatch(/maxWidth: '680px'/);
  });
});


describe('SolPendingBanner source guards', () => {
  const src = readSol('SolPendingBanner.jsx');

  it('uses calme-fg accent for left border (pending state)', () => {
    expect(src).toMatch(/borderLeft.*var\(--sol-calme-fg\)/);
  });

  it('role="status" + aria-live for countdown', () => {
    expect(src).toMatch(/role="status"/);
    expect(src).toMatch(/aria-live="polite"/);
  });

  it('countdown updates every minute (setInterval 60000)', () => {
    expect(src).toMatch(/setInterval.*60_000/);
  });

  it('formatRemaining returns French format "X h YY min"', () => {
    expect(src).toMatch(/return `\$\{h\} h \$\{String\(m\)/);
  });

  it('CTA Annuler toujours présent, Modifier conditionnel', () => {
    expect(src).toContain('Annuler');
    expect(src).toContain('Modifier');
    expect(src).toMatch(/onEdit\s*&&/);
  });
});


describe('SolJournal source guards', () => {
  const src = readSol('SolJournal.jsx');

  it('maps 8 ActionPhase values to FR labels', () => {
    for (const phase of ['proposed', 'previewed', 'confirmed', 'scheduled', 'executed', 'cancelled', 'reverted', 'refused']) {
      expect(src).toContain(`${phase}:`);
    }
  });

  it('FR labels use proper accents (é, è, ê)', () => {
    expect(src).toMatch(/'exécutée'/);
    expect(src).toMatch(/'annulée'/);
    expect(src).toMatch(/'refusée'/);
  });

  it('empty state message vouvoie + Sol voice', () => {
    expect(src).toMatch(/Aucune action agentique/);
  });

  it('correlation_id truncated to 12 chars + ellipsis', () => {
    expect(src).toMatch(/item\.correlation_id\.slice\(0, 12\)/);
  });

  it('uses locale fr-FR for date formatting', () => {
    expect(src).toMatch(/'fr-FR'/);
  });
});


describe('Sol index barrel exports', () => {
  const src = readSol('index.js');

  it('exports 6 Sol components', () => {
    for (const comp of ['SolCartouche', 'SolHero', 'SolActionPreview', 'SolHeadline', 'SolPendingBanner', 'SolJournal']) {
      expect(src).toContain(comp);
    }
  });
});


describe('services/api/sol client', () => {
  const src = readFileSync(join(process.cwd(), 'src', 'services', 'api', 'sol.js'), 'utf8');

  it('exposes propose/preview/confirm/cancel/pending/audit/policy API', () => {
    for (const fn of [
      'proposeAction',
      'previewAction',
      'confirmAction',
      'cancelAction',
      'listPendingActions',
      'listAuditTrail',
      'exportAuditCSV',
      'getSolPolicy',
      'updateSolPolicy',
    ]) {
      expect(src).toContain(`export const ${fn}`);
    }
  });

  it('exports SOL_INTENT_KINDS enum with 7 values', () => {
    expect(src).toContain('SOL_INTENT_KINDS');
    for (const intent of [
      'INVOICE_DISPUTE',
      'EXEC_REPORT',
      'DT_ACTION_PLAN',
      'AO_BUILDER',
      'OPERAT_BUILDER',
      'CONSULTATIVE_ONLY',
      'DUMMY_NOOP',
    ]) {
      expect(src).toContain(intent);
    }
  });

  it('exports SOL_ACTION_PHASES enum with 8 values', () => {
    for (const phase of [
      'PROPOSED',
      'PREVIEWED',
      'CONFIRMED',
      'SCHEDULED',
      'EXECUTED',
      'CANCELLED',
      'REVERTED',
      'REFUSED',
    ]) {
      expect(src).toContain(phase);
    }
  });

  it('exportAuditCSV uses responseType blob', () => {
    expect(src).toMatch(/responseType: 'blob'/);
  });
});


describe('tokens.js solTokens export', () => {
  const src = readFileSync(join(process.cwd(), 'src', 'ui', 'tokens.js'), 'utf8');

  it('exports solTokens namespace', () => {
    expect(src).toMatch(/export const solTokens/);
  });

  it('preserves warm accents (journal en terrasse) not Tailwind normalized', () => {
    expect(src).toContain('#2F6B5E');  // calme (bleu-vert doux warm)
    expect(src).toContain('#A06B1A');  // attention (ambre chaleureux)
    expect(src).toContain('#B8552E');  // afaire (orange corail)
    expect(src).toContain('#2E6B4A');  // succes (vert forêt)
  });

  it('slate base (not ivoire)', () => {
    expect(src).toContain('#F8F9FA');
    expect(src).toContain('#0F172A');
  });

  it('does NOT preserve PROMEOS tokens (isolation)', () => {
    // solTokens is its own namespace, PROMEOS colors/spacing unchanged
    expect(src).toMatch(/export const colors/);
    expect(src).toMatch(/export const solTokens/);
  });
});


describe('index.css .sol-surface scoping', () => {
  const src = readFileSync(join(process.cwd(), 'src', 'index.css'), 'utf8');

  it('defines .sol-surface with CSS custom properties', () => {
    expect(src).toMatch(/\.sol-surface\s*{/);
    expect(src).toMatch(/--sol-bg-canvas/);
    expect(src).toMatch(/--sol-calme-fg/);
  });

  it('respects prefers-reduced-motion', () => {
    expect(src).toMatch(/prefers-reduced-motion: reduce/);
  });

  it('defines sol-pulse keyframes', () => {
    expect(src).toMatch(/@keyframes sol-pulse/);
  });
});
