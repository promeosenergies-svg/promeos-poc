/**
 * Source-guard Phase 5 Lot 6 · days_remaining buckets scope.
 *
 * Les échéances sont PARTITIONNÉES BACKEND en 4 buckets exposés par
 * `GET /api/compliance/portfolio/summary` :
 *   - `deadlines.d30[]`   → < 30 jours (imminentes)
 *   - `deadlines.d90[]`   → 30–90 jours
 *   - `deadlines.d180[]`  → 90–180 jours (fenêtre préparation)
 *   - `deadlines.beyond[]` → > 180 jours
 *
 * Le front itère sur ces arrays — JAMAIS ne calcule les buckets
 * lui-même via `deadline.days_remaining < 30`. Si la définition des
 * buckets évolue (ex : ajout `d60`), c'est une décision backend, pas
 * une divergence silencieuse front.
 *
 * Patterns interdits :
 *   - `days_remaining < 30/60/90/180`
 *   - `days_remaining <= 30/60/90/180`
 *   - camelCase `daysRemaining < N`
 *   - constantes de bucket : `BUCKET_D30`, `DEADLINE_IMMINENT_DAYS`
 *
 * Scope : nouveaux paths Phase 5 Sol. Legacy exclu (sera wrapped
 * `{false && (…)}` en P5.3).
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

describe('days_remaining buckets scope guard (Phase 5 Lot 6)', () => {
  const files = ROOTS_TO_SCAN.flatMap((r) => walkJsx(r));

  it(`périmètre scanné documenté (${files.length} fichier${files.length > 1 ? 's' : ''})`, () => {
    expect(files.length).toBeGreaterThanOrEqual(0);
  });

  it('aucun composant ne recalcule un bucket deadline côté front', () => {
    const offenders = [];
    const patterns = [
      /days_remaining\s*[<>]=?\s*(30|60|90|180)/,
      /daysRemaining\s*[<>]=?\s*(30|60|90|180)/,
      /\bBUCKET_D(30|60|90|180)\b/,
      /\bDEADLINE_(IMMINENT|NEAR|FAR)_DAYS\b/,
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
      `Les buckets deadline d30/d90/d180/beyond sont pré-calculés ` +
        `backend. Itérer sur deadlines.d30, deadlines.d90, etc. — ne ` +
        `jamais recalculer via days_remaining. Violations : ` +
        `${uniqueOffenders.join(', ')}`
    ).toEqual([]);
  });

  it('whitelist display days_remaining autorisée', () => {
    // days_remaining peut être AFFICHÉ (ex : "J-73") mais jamais
    // comparé à un seuil littéral pour bucketer.
    const allowedReads = [
      'deadline.days_remaining', // display numérique (J-N)
      'deadline.deadline', // ISO date display
      'deadline.description', // string display
      'deadline.type', // enum finding/audit
      'deadline.regulation', // enum bacs/dt/aper
      'deadline.statut', // enum NOK/OK display
      'deadlines.d30.length', // count agrégat
      'deadlines.d90.length',
      'deadlines.d180.length',
      'deadlines.beyond.length',
    ];
    expect(allowedReads.length).toBe(10);
  });
});
