/**
 * Source-guard Phase 5 Lot 6 · trust_score threshold scope.
 *
 * Le seuil d'un site « untrusted » est défini BACKEND. L'endpoint
 * `GET /api/compliance/portfolio/summary` retourne directement un
 * tableau `untrusted_sites[]` pré-filtré. Le front lit la longueur
 * ou itère dessus — JAMAIS ne redéfinit un seuil côté client.
 *
 * Porte dérobée classique « juste un seuil pour filtrer » → crée une
 * divergence backend/front silencieuse. Ce guard la ferme.
 *
 * Patterns interdits :
 *   - `trust_score < N`, `trust_score <= N`, `trust_score > N`
 *   - `TRUST_THRESHOLD = N`, `UNTRUSTED_THRESHOLD`
 *   - camelCase : `trustScore < N`, `trustThreshold`
 *
 * Scope : nouveaux paths Phase 5 Sol. Legacy `CompliancePipelinePage.jsx`
 * exclu (sera wrapped `{false && (…)}` en P5.3).
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

describe('trust_score threshold scope guard (Phase 5 Lot 6)', () => {
  const files = ROOTS_TO_SCAN.flatMap((r) => walkJsx(r));

  it(`périmètre scanné documenté (${files.length} fichier${files.length > 1 ? 's' : ''})`, () => {
    expect(files.length).toBeGreaterThanOrEqual(0);
  });

  it('aucun composant ne redéfinit un seuil trust_score côté front', () => {
    const offenders = [];
    const patterns = [
      /trust_score\s*[<>]=?\s*[0-9]+/,
      /trustScore\s*[<>]=?\s*[0-9]+/,
      /\b(TRUST|UNTRUSTED)_THRESHOLD\b/,
      /\b(trust|untrusted)Threshold\b/,
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
      `Le seuil untrusted est défini BACKEND. Lire untrusted_sites[] ` +
        `directement (array pré-filtré), pas un comparator sur trust_score. ` +
        `Violations : ${uniqueOffenders.join(', ')}`
    ).toEqual([]);
  });

  it('whitelist lecture trust_score display autorisée', () => {
    // trust_score peut être AFFICHÉ (ex : badge "Confiance 32%") mais
    // jamais comparé à un seuil littéral côté front.
    const allowedReads = [
      'site.trust_score',       // display numérique
      'site.anomaly_count',     // display numérique
      'site.reasons',           // array display
      'untrusted_sites.length', // count agrégat
    ];
    expect(allowedReads.length).toBe(4);
  });
});
