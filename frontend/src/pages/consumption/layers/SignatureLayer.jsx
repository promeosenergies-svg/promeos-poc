/**
 * PROMEOS — SignatureLayer
 * Composable chart layer: rolling 7-day average (consumption signature).
 * Detects baseline shifts when overlaid on hourly/daily timeseries.
 *
 * Props:
 *   readings  {object[]}  array of { date, kwh } sorted by date
 *   visible   {boolean}   show/hide the layer (default true)
 *
 * The layer pre-computes a rolling 7-period mean and attaches it
 * as dataKey="signature" to the data via a WeakMap-free approach
 * (data must already have "signature" key OR this layer is used alongside
 * a data enrichment step).
 *
 * When used inside ExplorerChart the parent must include "signature" in
 * its data array. For simplicity, SignatureLayer exports a helper to
 * enrich raw data:  enrichWithSignature(data, window=7)
 */
import { Line } from 'recharts';

/**
 * Enrich a data array with rolling average.
 * @param {object[]} data  — array of { [key]: number, ... }
 * @param {string} valueKey — key to average (default 'kwh')
 * @param {number} window   — rolling window size (default 7)
 * @returns {object[]} same array with added "signature" key
 */
export function enrichWithSignature(data = [], valueKey = 'kwh', window = 7) {
  return data.map((point, i) => {
    const slice = data.slice(Math.max(0, i - window + 1), i + 1);
    const vals = slice.map(p => p[valueKey]).filter(v => v != null);
    const avg = vals.length ? vals.reduce((s, v) => s + v, 0) / vals.length : null;
    return { ...point, signature: avg != null ? +avg.toFixed(2) : null };
  });
}

/**
 * SignatureLayer — renders the signature line inside a ComposedChart.
 */
export default function SignatureLayer({ visible = true }) {
  if (!visible) return null;

  return (
    <Line
      type="monotone"
      dataKey="signature"
      stroke="#8b5cf6"
      strokeWidth={2}
      strokeDasharray="5 5"
      dot={false}
      name="Signature (moy. 7j)"
      connectNulls
    />
  );
}
