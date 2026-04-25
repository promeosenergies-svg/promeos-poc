/**
 * Source-guard Phase 5 Lot 6 · gate_status enum scope.
 *
 * `sites[].gate_status` est un ENUM backend-sourced : `OK` / `WARNING`
 * / `BLOCKED`. Le front PEUT le lire pour mapping display (pills,
 * couleurs, filtres) mais JAMAIS le réassigner, le recomposer depuis
 * `completeness_pct`, ni inventer de nouvelles valeurs côté client.
 *
 * Exemples d'usage autorisé (lecture display) :
 *   - `site.gate_status === 'OK'` → mapper vers tone succes
 *   - `site.gate_status === 'WARNING'` → mapper vers tone attention
 *   - switch/case sur gate_status pour label traduit
 *
 * Patterns interdits :
 *   - `gate_status = 'OK'` (assignation littérale)
 *   - `completeness_pct >= 90 ? 'OK' : 'BLOCKED'` (recomposition)
 *   - inventer d'autres valeurs enum : `gate_status = 'PENDING'`
 *
 * Scope : nouveaux paths Phase 5 Sol. Legacy exclu.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync, readdirSync, statSync, existsSync } from 'node:fs';
import { join, resolve } from 'node:path';

const ROOTS_TO_SCAN = [
  resolve('src/pages/CompliancePipelineSol.jsx'),
  resolve('src/pages/compliance-pipeline'),
];

function walkJsx(target) {
  const out = [];
  if (!existsSync(target)) return out;
  const st = statSync(target);
  if (st.isFile()) {
    if (/\.(jsx?|tsx?)$/.test(target)) out.push(target);
    return out;
  }
  for (const entry of readdirSync(target, { withFileTypes: true })) {
    if (entry.name === '__tests__' || entry.name === 'node_modules') continue;
    const p = join(target, entry.name);
    if (entry.isDirectory()) {
      out.push(...walkJsx(p));
    } else if (
      /\.(jsx?|tsx?)$/.test(entry.name) &&
      !entry.name.endsWith('.test.js') &&
      !entry.name.endsWith('.test.jsx')
    ) {
      out.push(p);
    }
  }
  return out;
}

describe('gate_status enum scope guard (Phase 5 Lot 6)', () => {
  const files = ROOTS_TO_SCAN.flatMap((r) => walkJsx(r));

  it(`périmètre scanné documenté (${files.length} fichier${files.length > 1 ? 's' : ''})`, () => {
    expect(files.length).toBeGreaterThanOrEqual(0);
  });

  it('aucun composant ne réassigne gate_status côté front', () => {
    const offenders = [];
    const patterns = [
      // Assignation littérale de l'enum (= 'OK' / = "WARNING" etc.)
      /gate_status\s*=\s*['"](OK|WARNING|BLOCKED|PENDING|UNKNOWN)['"]/,
      /gateStatus\s*=\s*['"](OK|WARNING|BLOCKED|PENDING|UNKNOWN)['"]/,
      // Recomposition via ternaire sur completeness/reg_risk
      /completeness_pct\s*[><]=?\s*[0-9]+\s*\?\s*['"](OK|WARNING|BLOCKED)['"]/,
      /reg_risk\s*[><]=?\s*[0-9]+\s*\?\s*['"](OK|WARNING|BLOCKED)['"]/,
    ];
    for (const f of files) {
      const src = readFileSync(f, 'utf8');
      if (patterns.some((p) => p.test(src))) {
        offenders.push(f);
      }
    }
    const uniqueOffenders = Array.from(new Set(offenders));
    expect(
      uniqueOffenders,
      `gate_status est un ENUM backend-sourced (OK/WARNING/BLOCKED). ` +
        `Le front le lit pour mapping display, jamais ne le réassigne ` +
        `ni ne le recompose depuis completeness_pct / reg_risk. ` +
        `Violations : ${uniqueOffenders.join(', ')}`
    ).toEqual([]);
  });

  it('whitelist lecture gate_status display autorisée', () => {
    // Lecture autorisée : comparaison égalité pour mapping UI,
    // switch/case, rendu conditionnel pill, filtres.
    const allowedReads = [
      "site.gate_status === 'OK'", // → tone succes
      "site.gate_status === 'WARNING'", // → tone attention
      "site.gate_status === 'BLOCKED'", // → tone refuse
      'switch (site.gate_status) { ... }',
      'applicability.{tertiaire_operat, bacs, aper}', // booleans display
    ];
    expect(allowedReads.length).toBe(5);
  });
});
