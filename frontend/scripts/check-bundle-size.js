/**
 * PROMEOS — Bundle Size Budget Check
 * Run after `npm run build`. Reads dist/assets/ and asserts total size < budget.
 * No external dependencies — uses only Node.js built-in fs/path.
 *
 * Usage: node scripts/check-bundle-size.js
 * Override thresholds via env: PROMEOS_BUNDLE_JS_KB=600 PROMEOS_BUNDLE_CSS_KB=80
 */
import { readdirSync, statSync } from 'node:fs';
import { join, extname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = fileURLToPath(new URL('.', import.meta.url));
const DIST_DIR = join(__dirname, '..', 'dist', 'assets');

// Thresholds in KB (overridable via env vars)
const BUDGET = {
  js_kb: parseInt(process.env.PROMEOS_BUNDLE_JS_KB || '1500', 10),
  css_kb: parseInt(process.env.PROMEOS_BUNDLE_CSS_KB || '100', 10),
};

function measureAssets(dir) {
  let jsBytes = 0;
  let cssBytes = 0;
  const files = [];

  try {
    for (const name of readdirSync(dir)) {
      const full = join(dir, name);
      const size = statSync(full).size;
      const ext = extname(name).toLowerCase();
      if (ext === '.js') jsBytes += size;
      if (ext === '.css') cssBytes += size;
      files.push({ name, size, ext });
    }
  } catch {
    console.error(`ERROR: Cannot read ${dir}. Did you run "npm run build" first?`);
    process.exit(2);
  }

  return { jsBytes, cssBytes, files };
}

const { jsBytes, cssBytes, files } = measureAssets(DIST_DIR);
const jsKb = Math.round(jsBytes / 1024);
const cssKb = Math.round(cssBytes / 1024);

console.log('=== PROMEOS Bundle Size Budget ===');
console.log(`JS total:  ${jsKb} KB  (budget: ${BUDGET.js_kb} KB)`);
console.log(`CSS total: ${cssKb} KB (budget: ${BUDGET.css_kb} KB)`);
console.log('');

// Top 5 largest JS files
const topJs = files
  .filter(f => f.ext === '.js')
  .sort((a, b) => b.size - a.size)
  .slice(0, 5);
if (topJs.length) {
  console.log('Top JS chunks:');
  topJs.forEach(f => console.log(`  ${f.name}  ${Math.round(f.size / 1024)} KB`));
  console.log('');
}

let failed = false;
if (jsKb > BUDGET.js_kb) {
  console.error(`FAIL: JS bundle ${jsKb} KB exceeds budget ${BUDGET.js_kb} KB`);
  failed = true;
}
if (cssKb > BUDGET.css_kb) {
  console.error(`FAIL: CSS bundle ${cssKb} KB exceeds budget ${BUDGET.css_kb} KB`);
  failed = true;
}

if (failed) {
  process.exit(1);
} else {
  console.log('PASS: All bundle sizes within budget.');
}
