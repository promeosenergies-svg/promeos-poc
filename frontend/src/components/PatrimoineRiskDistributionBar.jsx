/**
 * PatrimoineRiskDistributionBar — V64
 *
 * Barre de distribution du risque financier (OK / À surveiller / Critique).
 * Pas de Card wrapper — destiné à être inséré dans une Card existante.
 *
 * Algorithme : quantiles p40/p80 sur le tableau des risques.
 * Cas spécial N < 8 : top1 critique, next2 à surveiller, reste OK.
 */
import React from 'react';

/* ── Utilitaire formatage ── */

function fmtK(n) {
  if (!n || n <= 0) return '0 €';
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)} M€`;
  if (n >= 1_000) return `${Math.round(n / 1_000)} k€`;
  return `${Math.round(n)} €`;
}

/* ── Calcul des buckets ── */

/**
 * Calcule les buckets OK / À surveiller / Critique depuis un tableau de risques.
 *
 * @param {number[]} risks - Tableau de valeurs de risque (€). Peut contenir des zéros.
 * @returns {{ ok: number, warn: number, critical: number, thresholds: { p40: number, p80: number } }}
 */
export function computeRiskBuckets(risks) {
  const n = risks.length;
  if (n === 0) return { ok: 0, warn: 0, critical: 0, thresholds: { p40: 0, p80: 0 } };

  const allZero = risks.every((r) => r === 0);
  if (allZero) return { ok: n, warn: 0, critical: 0, thresholds: { p40: 0, p80: 0 } };

  const sorted = [...risks].sort((a, b) => a - b);
  const p40 = sorted[Math.floor(0.4 * (n - 1))];
  const p80 = sorted[Math.floor(0.8 * (n - 1))];

  if (n < 8) {
    // Petite population : classement fixe
    const critical = 1;
    const warn = Math.min(2, n - 1);
    const ok = n - critical - warn;
    return { ok, warn, critical, thresholds: { p40, p80 } };
  }

  let ok = 0,
    warn = 0,
    critical = 0;
  for (const r of risks) {
    if (r <= p40) ok++;
    else if (r <= p80) warn++;
    else critical++;
  }
  return { ok, warn, critical, thresholds: { p40, p80 } };
}

/* ── Composant ── */

/**
 * Barre compacte de distribution du risque.
 * Nécessite que les sites aient un champ `total_risk_eur`, `risque_eur` ou `risk_eur`.
 *
 * @param {{ sites: Array }} props
 */
export default function PatrimoineRiskDistributionBar({ sites }) {
  if (!sites || sites.length === 0) return null;

  const risks = sites.map((s) => Number(s.total_risk_eur ?? s.risque_eur ?? s.risk_eur ?? 0));
  const { ok, warn, critical, thresholds } = computeRiskBuckets(risks);
  const n = risks.length;

  const okPct = (ok / n) * 100;
  const warnPct = (warn / n) * 100;
  const critPct = (critical / n) * 100;

  const tooltip = `Basé sur quantiles du risque (€/site) — p40 : ${fmtK(thresholds.p40)}, p80 : ${fmtK(thresholds.p80)}`;

  const parts = [];
  if (ok > 0) parts.push({ key: 'ok', text: `${ok} OK`, cls: 'text-green-600 font-semibold' });
  if (warn > 0)
    parts.push({ key: 'warn', text: `${warn} À surveiller`, cls: 'text-amber-600 font-semibold' });
  if (critical > 0)
    parts.push({ key: 'crit', text: `${critical} Critique`, cls: 'text-red-500 font-semibold' });

  return (
    <div className="flex items-center gap-3 py-1" title={tooltip}>
      {/* Barre segmentée */}
      <div
        className="flex h-2 rounded-full overflow-hidden flex-1 min-w-0 bg-gray-100"
        role="img"
        aria-label={`Distribution du risque : ${ok} OK, ${warn} à surveiller, ${critical} critique`}
      >
        {okPct > 0 && (
          <div className="bg-green-300 transition-all" style={{ width: `${okPct}%` }} />
        )}
        {warnPct > 0 && (
          <div className="bg-amber-400 transition-all" style={{ width: `${warnPct}%` }} />
        )}
        {critPct > 0 && (
          <div className="bg-red-500   transition-all" style={{ width: `${critPct}%` }} />
        )}
      </div>

      {/* Résumé textuel */}
      <span className="text-[11px] text-gray-500 whitespace-nowrap shrink-0 flex items-center gap-1.5">
        {parts.map((p, i) => (
          <React.Fragment key={p.key}>
            {i > 0 && <span className="text-gray-300">•</span>}
            <span className={p.cls}>{p.text}</span>
          </React.Fragment>
        ))}
      </span>
    </div>
  );
}
