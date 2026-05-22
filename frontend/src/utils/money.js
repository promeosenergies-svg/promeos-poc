/**
 * PROMEOS — Format € pour mode CFO M2-6.B.frontend.
 *
 * Sémantique CFO distincte de `utils/format.js` :
 *   - `format.js::fmtEur(0)` retourne `'—'` (convention KPI Sol : 0 = absence).
 *   - `money.js::formatEuros(0)` retourne `'0 €'` (CFO : 0 = mesure valide, ≠ NULL).
 *
 * Cardinaux Q16 audit Amine :
 *   - Pas de suffixe `'€/an'` tant qu'`impact_period`/`impact_basis` absent API.
 *     Tracé `M3-IMPACT-PERIOD-BASIS` (backlog).
 *   - `null`/`undefined`/`NaN` → `'—'` (tiret cadratin U+2014).
 *   - `0` (zéro valide) → `'0 €'` ou `'0 €'` selon mode (jamais `'—'`).
 */

const FR = 'fr-FR';
// Séparateur insécable inséré nativement par toLocaleString FR (U+202F narrow no-break space).
// Tiret cadratin U+2014 pour NULL (convention doctrine UI honnête).
const DASH = '—';

function _coerce(value) {
  if (value === null || value === undefined) return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

/**
 * Formate un montant en EUR.
 *
 * @param {number|string|null|undefined} value montant (ex: 12500, "47500.00")
 * @param {"full"|"compact"} [mode="full"]
 *   - `"full"`    : `"12 500 €"` (séparateur espace insécable, 0 décimale)
 *   - `"compact"` : `"12,5 k€"` (1 décimale max si ≥ 1000, sinon full)
 * @returns {string} `"12 500 €"` / `"12,5 k€"` / `"—"`
 */
export function formatEuros(value, mode = 'full') {
  const n = _coerce(value);
  if (n === null) return DASH;

  if (mode === 'compact' && Math.abs(n) >= 1000) {
    const k = n / 1000;
    return `${k.toLocaleString(FR, { minimumFractionDigits: 0, maximumFractionDigits: 1 })} k€`;
  }

  // mode "full" OU compact < 1000
  return `${n.toLocaleString(FR, { minimumFractionDigits: 0, maximumFractionDigits: 0 })} €`;
}

/**
 * Formate pour la colonne « Impact estimé » du Référentiel : bascule auto
 * `full` ↔ `compact` selon le seuil 10 000 € (lisibilité scan colonne CFO).
 *
 * @param {number|string|null|undefined} value
 * @returns {string} `"3 200 €"` (< 10 000) · `"35 k€"` (≥ 10 000) · `"—"` (NULL)
 */
export function formatEurosColumn(value) {
  const n = _coerce(value);
  if (n === null) return DASH;
  return Math.abs(n) >= 10000 ? formatEuros(n, 'compact') : formatEuros(n, 'full');
}
