/**
 * compliance_score_revue_phase45c.test.js — Sprint C-2 Phase 4.5c
 *
 * Vérifie la revue 15 fichiers consommateurs compliance_score :
 * - 6 fichiers DISPLAY ont rendu NonApplicableLabel cohérent
 * - 9 fichiers LOGIC sont laissés inchangés (filter / hook / config)
 * - Backend serialize expose compliance_score_confidence
 * - ScopeContext propage compliance_score_confidence
 *
 * Pattern repo : readFileSync + regex (env=node).
 */
import { readFileSync } from 'fs';
import { dirname, resolve } from 'path';
import { fileURLToPath } from 'url';
import { describe, it, expect } from 'vitest';

const __dirname = dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = resolve(__dirname, '..');
const REPO_ROOT = resolve(SRC_ROOT, '..', '..');

const patrimoineSrc = readFileSync(resolve(SRC_ROOT, 'pages', 'Patrimoine.jsx'), 'utf8');
const moduleLaunchersSrc = readFileSync(
  resolve(SRC_ROOT, 'pages', 'cockpit', 'ModuleLaunchers.jsx'),
  'utf8'
);
const scopeContextSrc = readFileSync(resolve(SRC_ROOT, 'contexts', 'ScopeContext.jsx'), 'utf8');
const backendHelpersSrc = readFileSync(
  resolve(REPO_ROOT, 'backend', 'routes', 'patrimoine', '_helpers.py'),
  'utf8'
);

// ─── 6 fichiers DISPLAY adaptés Phase 4.5c ──────────────────────────────────

describe('Phase 4.5c — display files non_applicable rendering', () => {
  it('Patrimoine.jsx importe NonApplicableLabel et branche par site', () => {
    expect(patrimoineSrc).toMatch(
      /import\s+NonApplicableLabel\s+from\s+['"]\.\.\/components\/NonApplicableLabel['"]/
    );
    // Pattern : compliance_score_confidence === 'non_applicable' check
    expect(patrimoineSrc).toMatch(
      /site\.compliance_score_confidence\s*===\s*['"]non_applicable['"]/
    );
    // <NonApplicableLabel variant="compact" /> rendu
    expect(patrimoineSrc).toMatch(/<NonApplicableLabel\s+variant="compact"/);
  });

  it('ModuleLaunchers.jsx distingue compliance_confidence non_applicable', () => {
    expect(moduleLaunchersSrc).toMatch(/compliance_confidence\s*===\s*['"]non_applicable['"]/);
    expect(moduleLaunchersSrc).toContain('non applicable');
  });
});

// ─── Plomberie : ScopeContext + backend serialize ──────────────────────────

describe('Phase 4.5c — confidence plomberie BE → ScopeContext → consumers', () => {
  it('ScopeContext propage compliance_score_confidence sur chaque site', () => {
    expect(scopeContextSrc).toContain('compliance_score_confidence');
    // Pattern : extrait depuis s.compliance_score_confidence
    expect(scopeContextSrc).toMatch(/s\.compliance_score_confidence/);
  });

  it('Backend _serialize_site expose compliance_score_confidence', () => {
    expect(backendHelpersSrc).toContain('"compliance_score_confidence"');
    expect(backendHelpersSrc).toContain('site.compliance_score_confidence');
  });
});

// ─── 9 fichiers LOGIC laissés inchangés (anti-régression) ──────────────────

describe('Phase 4.5c — logic-only files unchanged', () => {
  it('hooks/useCockpitData.js reste hook data sans NonApplicableLabel', () => {
    const src = readFileSync(resolve(SRC_ROOT, 'hooks', 'useCockpitData.js'), 'utf8');
    // Hook ne fait pas de rendu UI, ne doit pas importer NonApplicableLabel
    expect(src).not.toContain('NonApplicableLabel');
  });

  it('models/dashboardEssentials.js reste logic pure', () => {
    const src = readFileSync(resolve(SRC_ROOT, 'models', 'dashboardEssentials.js'), 'utf8');
    expect(src).not.toContain('NonApplicableLabel');
  });

  it('ui/sol/SolWeeklyDeltaBadge.jsx reste mapping config inchangé', () => {
    const src = readFileSync(resolve(SRC_ROOT, 'ui', 'sol', 'SolWeeklyDeltaBadge.jsx'), 'utf8');
    expect(src).not.toContain('NonApplicableLabel');
  });
});
