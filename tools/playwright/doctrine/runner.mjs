/**
 * Runner orchestrateur — exécute les 8 tests doctrinaux et synthétise.
 *
 * Statut Sprint 0bis : T4 + T7 opérationnels. T1/T2/T6/T8 stubs avec
 * activation Sprint 1+ (LLM-eval Claude API + chantier α + scope élargi).
 *
 * Usage : node tools/playwright/doctrine/runner.mjs
 * Output : tools/playwright/doctrine/results/{timestamp}/synthesis.md
 */
import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';

const ROOT = '/Users/amine/projects/promeos-poc';
const TESTS_DIR = path.join(ROOT, 'tools/playwright/doctrine');
const OUT_DIR = path.join(
  TESTS_DIR,
  'results',
  new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19) + '-synthesis',
);

const TESTS = [
  { id: 'T1', name: '3 secondes', file: null, status: 'TODO', sprint: 'S1.1' },
  { id: 'T2', name: 'Dirigeant non-sachant', file: null, status: 'TODO', sprint: 'S1.1' },
  { id: 'T3', name: 'Grand écart archetype', file: null, status: 'TODO', sprint: 'S3' },
  { id: 'T4', name: 'Densité §4', file: 'test_t4_density.mjs', status: 'ACTIVE', sprint: 'S0bis' },
  { id: 'T5', name: 'Standalone module', file: null, status: 'MANUAL', sprint: 'S6' },
  { id: 'T6', name: 'Jour J vs J+1', file: null, status: 'TODO', sprint: 'S2' },
  { id: 'T7', name: 'Transformation acronymes §10', file: 'test_t7_acronyms.mjs', status: 'ACTIVE', sprint: 'S0bis' },
  { id: 'T8', name: 'Emplacement <2 clics', file: null, status: 'TODO', sprint: 'S1.1' },
];

fs.mkdirSync(OUT_DIR, { recursive: true });

const results = [];
for (const t of TESTS) {
  if (t.status !== 'ACTIVE') {
    results.push({ ...t, verdict: 'SKIP', reason: `Activation ${t.sprint}` });
    continue;
  }
  const start = Date.now();
  try {
    execSync(`node ${path.join(TESTS_DIR, t.file)}`, {
      stdio: 'inherit',
      cwd: ROOT,
    });
    results.push({ ...t, verdict: 'PASS', durationMs: Date.now() - start });
  } catch (e) {
    results.push({ ...t, verdict: 'FAIL', durationMs: Date.now() - start, error: e.message });
  }
}

const passCount = results.filter((r) => r.verdict === 'PASS').length;
const failCount = results.filter((r) => r.verdict === 'FAIL').length;
const skipCount = results.filter((r) => r.verdict === 'SKIP').length;
const activeCount = passCount + failCount;
const score = activeCount > 0 ? Math.round((passCount / activeCount) * 100) : 0;

let md = `# Synthèse tests doctrinaux PROMEOS Sol v1.0.1\n\n`;
md += `**Date** : ${new Date().toISOString()}\n`;
md += `**Score active** : ${passCount}/${activeCount} PASS (${score}%) · ${skipCount} SKIP (activation prochains sprints)\n\n`;
md += `## Résultats par test\n\n`;
md += `| Test | Nom | Statut | Verdict | Sprint activation |\n`;
md += `|---|---|---|---|---|\n`;
for (const r of results) {
  const verdictIcon = r.verdict === 'PASS' ? '✅' : r.verdict === 'FAIL' ? '❌' : '⏳';
  md += `| ${r.id} | ${r.name} | ${r.status} | ${verdictIcon} ${r.verdict} | ${r.sprint} |\n`;
}
md += `\n`;
md += `## Tests à activer prochains sprints\n\n`;
md += `- **S1.1** : T1 (3 secondes), T2 (non-sachant) via Claude API LLM-eval ; T8 (emplacement <2 clics)\n`;
md += `- **S2** : T6 (J vs J+1) — chantier α moteur d'événements\n`;
md += `- **S3** : T3 (grand écart archetype) — chantier β multi-archetype\n`;
md += `- **S6** : T5 (standalone) — checklist business case manuel\n\n`;
md += `## Référence\n\n`;
md += `- Doctrine §7 : \`docs/vision/promeos_sol_doctrine.md\`\n`;
md += `- Source-guards pytest : \`backend/tests/test_doctrine_sol_source_guards.py\`\n`;
md += `- README pattern : \`tools/playwright/doctrine/README.md\`\n`;

fs.writeFileSync(path.join(OUT_DIR, 'synthesis.md'), md);
fs.writeFileSync(path.join(OUT_DIR, 'synthesis.json'), JSON.stringify(results, null, 2));

console.log(`\n=== Synthèse ${score}% (${passCount}/${activeCount}) — output ${OUT_DIR}`);
process.exit(failCount > 0 ? 1 : 0);
