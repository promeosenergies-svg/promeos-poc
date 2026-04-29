/**
 * SolKpiMonthlyVsN1 — KPI 2 du triptyque Pilotage Sol2 v1.1.
 *
 * Phase 2.1bis du sprint refonte cockpit dual sol2 (29/04/2026). Composant
 * pur display Sol qui matérialise le swap "Surconso 7j → Conso mois courant
 * vs N-1 DJU-ajustée" (cible maquette v1.1).
 *
 * Cible maquette : `docs/maquettes/cockpit-sol2/cockpit-pilotage-briefing-jour.html`
 * lignes 258-268 (KPI 2 du triptyque temporel multi-échelle court/moyen/contractuel).
 *
 * Doctrine §8.1 (zero business logic frontend) : consomme directement
 * `_facts.consumption.monthly_vs_n1` produit par `cockpit_facts_service.py`
 * (Phase 1.3.a) qui agrège MeterReading + correction DJU via baseline_service.B.
 *
 * Tooltip canonique : « avril 2026 (j 1-27) vs avril 2025 (j 1-27 normalisé)
 * · Baseline B DJU-ajustée · r² 0,87 · calibrée 20/04/2026 ».
 *
 * Couleur delta (palette tokens Sol) :
 *   - Neutre   |delta| < 5 %
 *   - Warning  5 % ≤ |delta| < 15 %
 *   - Danger   |delta| ≥ 15 %
 *
 * Props :
 *   - data : objet monthly_vs_n1 (8 champs canoniques) ou null
 */
function fmtMwh(v) {
  if (v == null || !Number.isFinite(v)) return '—';
  return `${Math.round(v)
    .toLocaleString('fr-FR')
    .replace(/\u202f/g, ' ')} MWh`;
}

function fmtDate(iso) {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    });
  } catch {
    return iso;
  }
}

function deltaSeverity(deltaPct) {
  if (deltaPct == null || !Number.isFinite(deltaPct)) return 'neutral';
  const abs = Math.abs(deltaPct);
  if (abs < 5) return 'neutral';
  if (abs < 15) return 'warning';
  return 'danger';
}

const SEVERITY_TOKEN = {
  neutral: 'var(--sol-ink-500, #5a5853)',
  warning: 'var(--sol-attention-fg, #854f0b)',
  danger: 'var(--sol-refuse-fg, #a32d2d)',
};

export default function SolKpiMonthlyVsN1({ data, className = '' }) {
  if (!data || data.current_month_mwh == null) return null;

  const {
    current_month_label = '',
    current_month_mwh,
    previous_year_month_normalized_mwh = null,
    delta_pct_dju_adjusted = null,
    baseline_method = 'b_dju_adjusted',
    calibration_date = null,
    r_squared = null,
    confidence = '',
  } = data;

  const severity = deltaSeverity(delta_pct_dju_adjusted);
  const deltaSign = delta_pct_dju_adjusted != null && delta_pct_dju_adjusted >= 0 ? '+' : '';
  const deltaLabel =
    delta_pct_dju_adjusted != null ? `${deltaSign}${Math.round(delta_pct_dju_adjusted)} %` : '—';

  const tooltipParts = [];
  if (current_month_label) tooltipParts.push(current_month_label);
  if (previous_year_month_normalized_mwh != null) {
    const prevYearLabel = current_month_label.replace(/\d{4}/, (y) => String(parseInt(y, 10) - 1));
    tooltipParts.push(`vs ${prevYearLabel || 'année N-1'} (normalisé)`);
  }
  tooltipParts.push(
    baseline_method === 'b_dju_adjusted' ? 'Baseline B DJU-ajustée' : `Baseline ${baseline_method}`
  );
  if (r_squared != null) {
    tooltipParts.push(`r² ${Number(r_squared).toFixed(2).replace('.', ',')}`);
  }
  if (calibration_date) {
    tooltipParts.push(`calibrée ${fmtDate(calibration_date)}`);
  }
  const tooltip = tooltipParts.join(' · ');

  return (
    <div
      data-testid="sol-kpi-monthly-vs-n1"
      data-severity={severity}
      className={`flex flex-col gap-1.5 rounded-md px-4 py-3 ${className}`}
      style={{
        background: 'var(--sol-bg-canvas, #f7f5ef)',
        border: '0.5px solid var(--sol-line, rgba(26,24,21,.12))',
      }}
    >
      <div
        className="flex items-center gap-1.5 text-[11px] uppercase tracking-wider"
        style={{
          color: 'var(--sol-ink-400, #8a8780)',
          fontFamily: 'var(--font-mono, "JetBrains Mono", ui-monospace, monospace)',
        }}
      >
        <span>Conso mois courant</span>
        <span
          aria-label={tooltip}
          title={tooltip}
          data-testid="sol-kpi-monthly-tooltip"
          className="cursor-help select-none"
          style={{ borderBottom: '1px dotted currentColor' }}
        >
          ?
        </span>
      </div>
      <div className="flex items-baseline gap-2 flex-wrap">
        <span
          data-testid="sol-kpi-monthly-value"
          style={{
            fontFamily: 'var(--font-serif, "Fraunces", Georgia, serif)',
            fontSize: '28px',
            fontWeight: 500,
            lineHeight: 1,
            color: 'var(--sol-ink-900, #1a1815)',
          }}
        >
          {fmtMwh(current_month_mwh)}
        </span>
        <span
          data-testid="sol-kpi-monthly-delta"
          className="text-xs font-medium"
          style={{ color: SEVERITY_TOKEN[severity] }}
        >
          {deltaLabel} vs N−1
        </span>
      </div>
      <div
        className="text-[10.5px]"
        style={{
          color: 'var(--sol-ink-400, #8a8780)',
          fontFamily: 'var(--font-mono, "JetBrains Mono", ui-monospace, monospace)',
        }}
      >
        DJU-ajusté
        {confidence ? ` · confiance ${confidence}` : ''}
      </div>
    </div>
  );
}
