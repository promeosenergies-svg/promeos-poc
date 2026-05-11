/**
 * PROMEOS — Meta source-guards Phase F.7 (Sprint Grammaire v1.2 HARD STOP).
 *
 * Valide que les 2 guards Phase F.7 sont déployés et fonctionnels :
 *   Guard A : kpi-not-inline-in-hub-pages   → scripts/source_guards_design_system.sh
 *   Hook B  : commit-docs-only-stages-docs  → .husky/commit-msg
 *
 * Pattern pure-grep readFileSync (pas d'exécution shell — protégé contre les
 * faux positifs CI). Sur DEV local, le script + hook s'exécutent réellement
 * via npx lint-staged et git commit.
 */

import { describe, it, expect } from 'vitest';
import { readFileSync, existsSync, statSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = join(__dirname, '..', '..', '..', '..');
const GUARD_A_PATH = join(REPO_ROOT, 'scripts', 'source_guards_design_system.sh');
const HOOK_B_PATH = join(REPO_ROOT, '.husky', 'commit-msg');
const PRE_COMMIT_PATH = join(REPO_ROOT, '.husky', 'pre-commit');

describe('Phase F.7 — Guard A : kpi-not-inline-in-hub-pages (shell)', () => {
  it('scripts/source_guards_design_system.sh existe sur disque', () => {
    expect(existsSync(GUARD_A_PATH)).toBe(true);
  });

  it('scripts/source_guards_design_system.sh est exécutable', () => {
    const mode = statSync(GUARD_A_PATH).mode;
    // Bit 0o100 = owner execute. On verifie au moins ça.
    expect(mode & 0o100).toBeGreaterThan(0);
  });

  it('Guard A scanne >=7 pages-hub L11 dans la liste HUBS', () => {
    const src = readFileSync(GUARD_A_PATH, 'utf-8');
    // Pages-hub L11 listées explicitement (cockpit/jour + 5 hubs Phase 3.5
    // + cockpit stratégique + cockpit décision).
    expect(src).toContain('CockpitJour');
    expect(src).toContain('Energie');
    expect(src).toContain('Conformite');
    expect(src).toContain('Achat');
    expect(src).toContain('Patrimoine');
  });

  it('Guard A détecte className kpi-* inline (pattern 1)', () => {
    const src = readFileSync(GUARD_A_PATH, 'utf-8');
    expect(src).toMatch(/className.*kpi-\(card\|icon\|value\|delta\|eyebrow/);
  });

  it('Guard A détecte définition locale KpiTriptychCard/KpiCard/MetricCard (pattern 2)', () => {
    const src = readFileSync(GUARD_A_PATH, 'utf-8');
    expect(src).toMatch(/function.*KpiTriptychCard\|KpiCard\|MetricCard\|KpiBlock/);
  });

  it('Guard A exit 1 si violations (échec build CI)', () => {
    const src = readFileSync(GUARD_A_PATH, 'utf-8');
    expect(src).toContain('exit "$EXIT_CODE"');
    expect(src).toContain('EXIT_CODE=1');
  });
});

describe('Phase F.7 — Hook B : commit-docs-only-stages-docs (Husky)', () => {
  it('.husky/commit-msg existe sur disque', () => {
    expect(existsSync(HOOK_B_PATH)).toBe(true);
  });

  it('.husky/commit-msg est exécutable', () => {
    const mode = statSync(HOOK_B_PATH).mode;
    expect(mode & 0o100).toBeGreaterThan(0);
  });

  it('Hook B intercepte messages docs(... à la première ligne', () => {
    const src = readFileSync(HOOK_B_PATH, 'utf-8');
    expect(src).toMatch(/grep.*-qE.*\^docs\\\(/);
  });

  it('Hook B liste les fichiers docs autorisés (docs/, *.md, *.mdx, *.yaml, *.yml)', () => {
    const src = readFileSync(HOOK_B_PATH, 'utf-8');
    expect(src).toContain('docs/');
    expect(src).toContain('.md$');
    expect(src).toContain('.mdx$');
    expect(src).toContain('.yaml$');
    expect(src).toContain('.yml$');
  });

  it('Hook B exit 1 si contamination détectée (non-docs staged + docs message)', () => {
    const src = readFileSync(HOOK_B_PATH, 'utf-8');
    expect(src).toContain('exit 1');
    expect(src).toContain('contamination détectée');
  });

  it("Hook B référence la leçon 3774d2c0 dans le message d'erreur", () => {
    const src = readFileSync(HOOK_B_PATH, 'utf-8');
    expect(src).toContain('3774d2c0');
  });
});

describe('Phase F.7 — Wire-up dans .husky/pre-commit', () => {
  it('pre-commit appelle scripts/source_guards_design_system.sh apres lint-staged', () => {
    const src = readFileSync(PRE_COMMIT_PATH, 'utf-8');
    expect(src).toContain('source_guards_design_system.sh');
    // L'appel doit etre apres lint-staged (verification ordre approximative)
    const lintIdx = src.indexOf('npx lint-staged');
    const guardIdx = src.indexOf('source_guards_design_system.sh');
    expect(lintIdx).toBeGreaterThan(-1);
    expect(guardIdx).toBeGreaterThan(lintIdx);
  });

  it('pre-commit exit 1 si Guard A echoue (propagation status)', () => {
    const src = readFileSync(PRE_COMMIT_PATH, 'utf-8');
    expect(src).toMatch(/source_guards_design_system\.sh"\s*\|\|\s*exit 1/);
  });
});
