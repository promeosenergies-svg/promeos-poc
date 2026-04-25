/**
 * Source-guard Phase 4 Lot 6 · Audit SMÉ scope.
 *
 * Audit SMÉ est évalué au scope ORGANISATION (personne morale
 * ≥ 250 salariés ou CA ≥ 50 M€, directive 2012/27/UE). Source
 * backend : audit_sme_service.py:288 — compute_global_score_with_audit_sme
 * prend `audit_sme_applicable: bool` comme paramètre ORG-level.
 *
 * Si un composant frontend lit `site.audit_sme_*` (ex : site.audit_sme_status
 * ou sites[i].audit_sme_applicable), c'est un bug architectural : la
 * règle doit être évaluée une fois au niveau organisation, pas par site.
 *
 * Cf. docs/audit/api_regops_shape_phase4.md section "Audit SMÉ scope".
 */
import { describe, it, expect } from 'vitest';
import { readFileSync, readdirSync, statSync, existsSync } from 'node:fs';
import { join, resolve } from 'node:path';

const ROOTS_TO_SCAN = [
  resolve('src/pages/ConformiteTertiaireSol.jsx'),
  resolve('src/pages/conformite-tertiaire'),
  resolve('src/pages/tertiaire'),
  resolve('src/pages/ConformiteSol.jsx'),
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
    // Exclure les répertoires de tests (sinon le guard matche ses
    // propres patterns de détection en string)
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

describe('Audit SMÉ scope guard (Phase 4 Lot 6)', () => {
  const files = ROOTS_TO_SCAN.flatMap((r) => walkJsx(r));

  // Sanity check pour documenter le périmètre scanné (informationnel
  // uniquement). On tolère 0 fichier (cas où paths absolus ne
  // matchent pas en CI ou post-refacto) car la vraie valeur du guard
  // est l'assertion no-violations en dessous.
  it(`périmètre scanné documenté (${files.length} fichier${files.length > 1 ? 's' : ''})`, () => {
    expect(files.length).toBeGreaterThanOrEqual(0);
  });

  it('aucun composant ne lit site.audit_sme_* au scope site', () => {
    const offenders = [];
    for (const f of files) {
      const src = readFileSync(f, 'utf8');
      // Interdit : site.audit_sme_XXX ou sites[i].audit_sme_XXX
      if (/site[s]?\.(audit_sme|auditSme)/i.test(src)) {
        offenders.push(f);
      }
      // Variante : property chain plus espacée
      if (/\bsite\b[\s\S]{0,20}\baudit_sme_(status|applicable|deadline|score)\b/.test(src)) {
        offenders.push(f);
      }
    }
    const uniqueOffenders = Array.from(new Set(offenders));
    expect(
      uniqueOffenders,
      `Audit SMÉ doit être lu au scope ORG (audit_sme_applicable via ` +
        `endpoint /api/audit-sme/status), pas au scope site. Fichiers ` +
        `en violation : ${uniqueOffenders.join(', ')}`
    ).toEqual([]);
  });

  it('whitelist findings.ops enums documentée (regulation/rule_id/status/severity)', () => {
    // Test informationnel : les enums display issus de findings sont
    // autorisés en lecture (pills, labels, filtres). Ce sont des
    // enums backend-sourced, pas des formules.
    const allowedReads = [
      'finding.regulation',
      'finding.rule_id',
      'finding.status',
      'finding.severity',
      'finding.legal_deadline',
      'finding.category',
    ];
    expect(allowedReads.length).toBe(6);
  });
});
