/**
 * PROMEOS — Page Usages Énergétiques V1.2
 * Page pivot : Readiness + Plan de comptage + Top UES + Baselines + Dérives
 *            + Conformité par usage + Coût + Liens facture/contrat/achat + Export
 *
 * Route : /usages (intégrée dans App.jsx, pas de nouveau menu)
 */
import React, { useEffect, useState, useRef } from 'react';
import { useScope } from '../contexts/ScopeContext';
import { getUsagesDashboard } from '../services/api';
import { useNavigate } from 'react-router-dom';

// ── Helpers ──────────────────────────────────────────────────────────────

const fmt = (n, decimals = 0) => {
  if (n == null) return '—';
  return Number(n).toLocaleString('fr-FR', { maximumFractionDigits: decimals });
};

const severityColor = (sev) =>
  ({ critical: '#dc2626', high: '#ea580c', medium: '#d97706', low: '#65a30d' })[sev] || '#6b7280';

const levelBadge = (level) => {
  const map = {
    GREEN: { bg: '#dcfce7', color: '#166534', label: 'Prêt' },
    AMBER: { bg: '#fef3c7', color: '#92400e', label: 'Partiel' },
    RED: { bg: '#fee2e2', color: '#991b1b', label: 'Non prêt' },
  };
  return map[level] || map.RED;
};

const familyIcon = (family) =>
  ({
    thermique: '🌡️',
    eclairage: '💡',
    elec_specifique: '🖥️',
    process: '⚙️',
    mobilite: '🔌',
    auxiliaires: '📦',
  })[family] || '📊';

const dataSourceLabel = (src) =>
  ({
    mesure_directe: 'Mesuré',
    estimation_prorata: 'Estimé',
    baseline_stockee: 'Baseline',
    import_csv: 'Import',
    gtb_api: 'GTB',
    facturation: 'Facture',
    manuel: 'Manuel',
  })[src] ||
  src ||
  '—';

const dataSourceColor = (src) =>
  ({
    mesure_directe: '#166534',
    estimation_prorata: '#92400e',
    baseline_stockee: '#7c3aed',
    import_csv: '#1e40af',
    gtb_api: '#6d28d9',
    facturation: '#0e7490',
  })[src] || '#6b7280';

const trendIcon = (trend) =>
  ({
    amelioration: { icon: '↘', color: '#16a34a', label: 'Amélioration' },
    degradation: { icon: '↗', color: '#dc2626', label: 'Dégradation' },
    stable: { icon: '→', color: '#6b7280', label: 'Stable' },
  })[trend] || { icon: '?', color: '#9ca3af', label: '—' };

const priceSourceLabel = (src) =>
  ({ contrat: 'Prix contrat', facture: 'Prix moyen facturé', defaut: 'Prix par défaut' })[src] ||
  src;

// ── Shared styles ────────────────────────────────────────────────────────

const sectionStyle = {
  background: 'white',
  borderRadius: 12,
  padding: '20px 24px',
  marginBottom: 16,
  boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
};

const h2Style = {
  fontSize: 15,
  fontWeight: 700,
  color: '#111827',
  marginBottom: 12,
  display: 'flex',
  alignItems: 'center',
  gap: 8,
};

// ── Components ───────────────────────────────────────────────────────────

function ReadinessBadge({ score, level }) {
  const badge = levelBadge(level);
  return (
    <div
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 8,
        padding: '6px 14px',
        borderRadius: 8,
        background: badge.bg,
        color: badge.color,
        fontWeight: 600,
        fontSize: 14,
      }}
    >
      <span style={{ fontSize: 18, fontWeight: 700 }}>{score}/100</span>
      <span>{badge.label}</span>
    </div>
  );
}

function DataSourceBadge({ source }) {
  return (
    <span
      style={{
        display: 'inline-block',
        padding: '2px 8px',
        borderRadius: 4,
        fontSize: 11,
        fontWeight: 600,
        background: `${dataSourceColor(source)}18`,
        color: dataSourceColor(source),
        letterSpacing: 0.3,
      }}
    >
      {dataSourceLabel(source)}
    </span>
  );
}

function KpiCard({ label, value, unit, sub }) {
  return (
    <div
      style={{
        flex: '1 1 140px',
        padding: '14px 16px',
        background: '#f9fafb',
        borderRadius: 10,
        textAlign: 'center',
      }}
    >
      <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 700, color: '#111827' }}>
        {value}
        {unit && <span style={{ fontSize: 13, fontWeight: 400, color: '#6b7280' }}> {unit}</span>}
      </div>
      {sub && <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

function TrendBadge({ trend, ecart_pct }) {
  const t = trendIcon(trend);
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 3,
        fontSize: 12,
        fontWeight: 600,
        color: t.color,
      }}
      title={t.label}
    >
      <span style={{ fontSize: 16 }}>{t.icon}</span>
      {ecart_pct != null && (
        <span>
          {ecart_pct > 0 ? '+' : ''}
          {fmt(ecart_pct, 1)}%
        </span>
      )}
    </span>
  );
}

// ── V1.2: Baseline / Avant-Après ─────────────────────────────────────────

function BaselineSummary({ baselines }) {
  if (!baselines || baselines.length === 0) return null;

  const improving = baselines.filter((b) => b.trend === 'amelioration');
  const degrading = baselines.filter((b) => b.trend === 'degradation');
  const stable = baselines.filter((b) => b.trend === 'stable');

  const totalEcart = baselines.reduce((s, b) => s + (b.ecart_kwh || 0), 0);
  const totalEcartEur = Math.round(totalEcart * 0.18); // prix moyen

  const dominant =
    degrading.length > improving.length
      ? 'degradation'
      : improving.length > degrading.length
        ? 'amelioration'
        : 'stable';

  const dominantColor =
    dominant === 'amelioration' ? '#16a34a' : dominant === 'degradation' ? '#dc2626' : '#6b7280';

  return (
    <div
      style={{
        display: 'flex',
        gap: 12,
        flexWrap: 'wrap',
        marginBottom: 14,
        padding: '12px 16px',
        background:
          dominant === 'amelioration'
            ? '#f0fdf4'
            : dominant === 'degradation'
              ? '#fef2f2'
              : '#f9fafb',
        borderRadius: 8,
        border: `1px solid ${dominant === 'amelioration' ? '#bbf7d0' : dominant === 'degradation' ? '#fecaca' : '#e5e7eb'}`,
      }}
    >
      <div style={{ flex: '1 1 200px' }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: dominantColor, marginBottom: 4 }}>
          {dominant === 'amelioration'
            ? 'Tendance globale : amélioration'
            : dominant === 'degradation'
              ? 'Tendance globale : dégradation'
              : 'Tendance globale : stable'}
        </div>
        <div style={{ fontSize: 12, color: '#374151' }}>
          {improving.length > 0 && (
            <span style={{ color: '#16a34a', fontWeight: 600, marginRight: 12 }}>
              ↘ {improving.length} en amélioration
            </span>
          )}
          {degrading.length > 0 && (
            <span style={{ color: '#dc2626', fontWeight: 600, marginRight: 12 }}>
              ↗ {degrading.length} en dégradation
            </span>
          )}
          {stable.length > 0 && (
            <span style={{ color: '#6b7280', fontWeight: 500 }}>→ {stable.length} stable(s)</span>
          )}
        </div>
      </div>
      <div style={{ textAlign: 'right', minWidth: 160 }}>
        <div
          style={{
            fontSize: 18,
            fontWeight: 700,
            color: totalEcart > 0 ? '#dc2626' : totalEcart < 0 ? '#16a34a' : '#6b7280',
          }}
        >
          {totalEcart > 0 ? '+' : ''}
          {fmt(totalEcart)} kWh
        </div>
        <div style={{ fontSize: 11, color: '#6b7280' }}>
          {totalEcart > 0 ? 'Surconsommation' : totalEcart < 0 ? 'Économie' : 'Écart nul'} :{' '}
          {totalEcartEur > 0 ? '+' : ''}
          {fmt(totalEcartEur)} EUR/an estimé
        </div>
      </div>
    </div>
  );
}

function BaselineTable({ baselines }) {
  if (!baselines || baselines.length === 0) {
    return (
      <p style={{ color: '#9ca3af', fontStyle: 'italic', fontSize: 13 }}>
        Baselines non disponibles — données insuffisantes ou sous-compteurs non liés.
      </p>
    );
  }
  return (
    <div>
      <BaselineSummary baselines={baselines} />
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr style={{ borderBottom: '2px solid #e5e7eb', textAlign: 'left' }}>
            <th style={{ padding: '8px 6px' }}>Usage</th>
            <th style={{ padding: '8px 6px', textAlign: 'right' }}>Baseline kWh</th>
            <th style={{ padding: '8px 6px', textAlign: 'right' }}>Actuel kWh</th>
            <th style={{ padding: '8px 6px', textAlign: 'right' }}>Écart</th>
            <th style={{ padding: '8px 6px', textAlign: 'right' }}>IPE base</th>
            <th style={{ padding: '8px 6px', textAlign: 'right' }}>IPE actuel</th>
            <th style={{ padding: '8px 6px', textAlign: 'center' }}>Tendance</th>
            <th style={{ padding: '8px 6px', textAlign: 'center' }}>Source</th>
          </tr>
        </thead>
        <tbody>
          {baselines.map((b, i) => (
            <tr key={b.usage_id || i} style={{ borderBottom: '1px solid #f3f4f6' }}>
              <td style={{ padding: '8px 6px' }}>
                <span>{familyIcon(b.family)}</span>{' '}
                <span style={{ fontWeight: b.is_significant ? 600 : 400 }}>{b.label}</span>
                {b.actions_completed > 0 && (
                  <span
                    style={{
                      marginLeft: 6,
                      fontSize: 10,
                      padding: '1px 5px',
                      borderRadius: 3,
                      background: '#dcfce7',
                      color: '#166534',
                      fontWeight: 600,
                    }}
                  >
                    {b.actions_completed} action(s)
                  </span>
                )}
              </td>
              <td style={{ padding: '8px 6px', textAlign: 'right' }}>{fmt(b.kwh_baseline)}</td>
              <td style={{ padding: '8px 6px', textAlign: 'right', fontWeight: 600 }}>
                {fmt(b.kwh_current)}
              </td>
              <td
                style={{
                  padding: '8px 6px',
                  textAlign: 'right',
                  color: b.ecart_pct > 0 ? '#dc2626' : b.ecart_pct < 0 ? '#16a34a' : '#6b7280',
                  fontWeight: 600,
                }}
              >
                {b.ecart_kwh != null ? `${b.ecart_kwh > 0 ? '+' : ''}${fmt(b.ecart_kwh)}` : '—'}
              </td>
              <td style={{ padding: '8px 6px', textAlign: 'right', color: '#6b7280' }}>
                {b.ipe_baseline ? `${fmt(b.ipe_baseline, 1)}` : '—'}
              </td>
              <td style={{ padding: '8px 6px', textAlign: 'right', fontWeight: 500 }}>
                {b.ipe_current ? `${fmt(b.ipe_current, 1)}` : '—'}
              </td>
              <td style={{ padding: '8px 6px', textAlign: 'center' }}>
                <TrendBadge trend={b.trend} ecart_pct={b.ecart_pct} />
              </td>
              <td style={{ padding: '8px 6px', textAlign: 'center' }}>
                <DataSourceBadge source={b.data_source} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── UES Table (enrichi V1.2) ─────────────────────────────────────────────

function UesTable({ ues }) {
  if (!ues || ues.length === 0) {
    return (
      <p style={{ color: '#9ca3af', fontStyle: 'italic' }}>Aucun usage significatif détecté.</p>
    );
  }
  return (
    <div>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr style={{ borderBottom: '2px solid #e5e7eb', textAlign: 'left' }}>
            <th style={{ padding: '8px 6px' }}>Usage</th>
            <th style={{ padding: '8px 6px', textAlign: 'right' }}>kWh/an</th>
            <th style={{ padding: '8px 6px', textAlign: 'right' }}>Part</th>
            <th style={{ padding: '8px 6px', textAlign: 'right' }}>IPE kWh/m²</th>
            <th style={{ padding: '8px 6px', textAlign: 'center' }}>Source</th>
            <th style={{ padding: '8px 6px', textAlign: 'center' }}>Dérive</th>
          </tr>
        </thead>
        <tbody>
          {ues.map((u, i) => (
            <tr key={u.usage_id || i} style={{ borderBottom: '1px solid #f3f4f6' }}>
              <td style={{ padding: '8px 6px', display: 'flex', alignItems: 'center', gap: 6 }}>
                <span>{familyIcon(u.family)}</span>
                <span style={{ fontWeight: u.is_significant ? 600 : 400 }}>{u.label}</span>
                {u.is_significant && (
                  <span
                    style={{
                      fontSize: 10,
                      padding: '1px 5px',
                      borderRadius: 3,
                      background: '#dbeafe',
                      color: '#1e40af',
                      fontWeight: 600,
                    }}
                  >
                    UES
                  </span>
                )}
              </td>
              <td style={{ padding: '8px 6px', textAlign: 'right', fontWeight: 600 }}>
                {fmt(u.kwh)}
              </td>
              <td style={{ padding: '8px 6px', textAlign: 'right' }}>{fmt(u.pct_of_total, 1)}%</td>
              <td style={{ padding: '8px 6px', textAlign: 'right' }}>
                {u.ipe_kwh_m2 ? fmt(u.ipe_kwh_m2, 1) : '—'}
              </td>
              <td style={{ padding: '8px 6px', textAlign: 'center' }}>
                <DataSourceBadge source={u.data_source} />
              </td>
              <td style={{ padding: '8px 6px', textAlign: 'center' }}>
                {u.has_drift ? (
                  <span style={{ color: '#dc2626', fontWeight: 600 }}>+{fmt(u.drift_pct, 1)}%</span>
                ) : (
                  <span style={{ color: '#65a30d' }}>OK</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 8, fontStyle: 'italic' }}>
        UES = Usage Énergétique Significatif (critère ISO 50001). IPE = Indicateur de Performance
        Énergétique (kWh/m²/an).
      </div>
    </div>
  );
}

// ── Plan de comptage ─────────────────────────────────────────────────────

function MeteringPlanTree({ plan }) {
  if (!plan || !plan.meters || plan.meters.length === 0) {
    return <p style={{ color: '#9ca3af', fontStyle: 'italic' }}>Aucun compteur configuré.</p>;
  }
  return (
    <div>
      {plan.meters.map((m) => (
        <div key={m.id} style={{ marginBottom: 12 }}>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '8px 12px',
              background: '#f0f9ff',
              borderRadius: 8,
              fontWeight: 600,
              fontSize: 13,
            }}
          >
            <span>
              ⚡ {m.name} ({m.meter_id})
            </span>
            <span>{fmt(m.kwh)} kWh</span>
          </div>
          {m.sub_meters && m.sub_meters.length > 0 && (
            <div style={{ marginLeft: 24, marginTop: 4 }}>
              {m.sub_meters.map((s) => (
                <div
                  key={s.id}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '5px 10px',
                    borderLeft: '2px solid #93c5fd',
                    marginBottom: 2,
                    fontSize: 12,
                  }}
                >
                  <span>
                    └ {s.name}
                    {s.usage && (
                      <span
                        style={{
                          marginLeft: 6,
                          padding: '1px 6px',
                          borderRadius: 3,
                          background: '#ede9fe',
                          color: '#5b21b6',
                          fontSize: 10,
                          fontWeight: 600,
                        }}
                      >
                        {s.usage.label}
                      </span>
                    )}
                    <DataSourceBadge source={s.data_source} />
                  </span>
                  <span style={{ fontWeight: 500 }}>
                    {fmt(s.kwh)} kWh ({fmt(s.pct_of_principal, 1)}%)
                  </span>
                </div>
              ))}
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  padding: '4px 10px',
                  borderLeft: '2px dashed #d1d5db',
                  fontSize: 11,
                  color: '#6b7280',
                  fontStyle: 'italic',
                }}
              >
                <span>{m.delta_label}</span>
                <span>
                  {fmt(m.delta_kwh)} kWh ({fmt(m.delta_pct, 1)}%)
                </span>
              </div>
            </div>
          )}
          {m.sub_meters && m.sub_meters.length > 0 && (
            <div style={{ marginLeft: 24, marginTop: 4, fontSize: 11, color: '#6b7280' }}>
              Couverture sous-comptage : <strong>{fmt(m.coverage_pct, 1)}%</strong>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// ── Dérives ──────────────────────────────────────────────────────────────

function DriftCards({ drifts, navigate }) {
  if (!drifts || drifts.length === 0) {
    return <p style={{ color: '#65a30d', fontWeight: 500 }}>Aucune dérive active.</p>;
  }
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
      {drifts.slice(0, 5).map((d, i) => (
        <div
          key={d.insight_id || i}
          style={{
            flex: '1 1 280px',
            padding: '12px 14px',
            borderRadius: 10,
            border: `1px solid ${severityColor(d.severity)}40`,
            background: `${severityColor(d.severity)}08`,
          }}
        >
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: 4,
            }}
          >
            <span
              style={{
                fontSize: 11,
                padding: '2px 6px',
                borderRadius: 3,
                background: `${severityColor(d.severity)}20`,
                color: severityColor(d.severity),
                fontWeight: 600,
                textTransform: 'uppercase',
              }}
            >
              {d.severity}
            </span>
            {d.usage_label && (
              <span style={{ fontSize: 11, color: '#6b7280' }}>{d.usage_label}</span>
            )}
          </div>
          <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 6, lineHeight: 1.4 }}>
            {d.message}
          </div>
          <div style={{ fontSize: 12, color: '#6b7280' }}>
            Perte estimée : <strong>{fmt(d.estimated_loss_eur)} EUR/an</strong> (
            {fmt(d.estimated_loss_kwh)} kWh)
          </div>
          <button
            onClick={() => navigate('/diagnostic-conso')}
            style={{
              marginTop: 8,
              padding: '4px 10px',
              fontSize: 11,
              borderRadius: 5,
              border: '1px solid #d1d5db',
              background: 'white',
              cursor: 'pointer',
              fontWeight: 500,
            }}
          >
            Traiter →
          </button>
        </div>
      ))}
    </div>
  );
}

// ── Coût par usage ───────────────────────────────────────────────────────

function CostBreakdown({ cost }) {
  if (!cost || !cost.by_usage || cost.by_usage.length === 0) {
    return <p style={{ color: '#9ca3af', fontStyle: 'italic' }}>Aucune ventilation disponible.</p>;
  }
  const maxKwh = Math.max(...cost.by_usage.map((u) => u.kwh));
  return (
    <div>
      {cost.by_usage.map((u, i) => (
        <div key={i} style={{ marginBottom: 8 }}>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              fontSize: 12,
              marginBottom: 2,
            }}
          >
            <span style={{ fontWeight: 500 }}>{u.label}</span>
            <span>
              {fmt(u.eur)} EUR ({fmt(u.pct_of_total, 1)}%)
            </span>
          </div>
          <div style={{ height: 8, background: '#f3f4f6', borderRadius: 4, overflow: 'hidden' }}>
            <div
              style={{
                height: '100%',
                width: `${(u.kwh / maxKwh) * 100}%`,
                background: '#3b82f6',
                borderRadius: 4,
                transition: 'width 0.5s ease',
              }}
            />
          </div>
        </div>
      ))}
      {cost.uncovered_kwh > 0 && (
        <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 6, fontStyle: 'italic' }}>
          Non couvert : {fmt(cost.uncovered_kwh)} kWh ({fmt(cost.uncovered_eur)} EUR) — couverture{' '}
          {fmt(cost.coverage_pct, 1)}%
        </div>
      )}
    </div>
  );
}

// ── V1.2: Widget Conformité par usage ────────────────────────────────────

function ComplianceWidget({ compliance, navigate }) {
  if (!compliance) return null;
  const { bacs_score, usage_coverage, top_risk, items } = compliance;
  const concerned = items?.filter((it) => it.concerned_by_bacs || it.concerned_by_dt) || [];
  if (concerned.length === 0 && !bacs_score) return null;

  return (
    <div>
      {/* Score + couverture */}
      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 14 }}>
        {bacs_score != null && (
          <div
            style={{
              padding: '10px 16px',
              background: bacs_score >= 70 ? '#dcfce7' : bacs_score >= 40 ? '#fef3c7' : '#fee2e2',
              borderRadius: 8,
              textAlign: 'center',
              minWidth: 120,
            }}
          >
            <div style={{ fontSize: 11, color: '#6b7280' }}>Score BACS</div>
            <div style={{ fontSize: 22, fontWeight: 700 }}>{fmt(bacs_score, 0)}/100</div>
          </div>
        )}
        <div
          style={{
            padding: '10px 16px',
            background: '#f0f9ff',
            borderRadius: 8,
            textAlign: 'center',
            minWidth: 120,
          }}
        >
          <div style={{ fontSize: 11, color: '#6b7280' }}>Couverture BACS</div>
          <div style={{ fontSize: 22, fontWeight: 700 }}>
            {fmt(usage_coverage?.coverage_pct, 0)}%
          </div>
          <div style={{ fontSize: 11, color: '#6b7280' }}>
            {usage_coverage?.bacs_covered}/{usage_coverage?.bacs_concerned} usages
          </div>
        </div>
      </div>

      {/* Détail par usage */}
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
        <thead>
          <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
            <th style={{ padding: '6px', textAlign: 'left' }}>Usage</th>
            <th style={{ padding: '6px', textAlign: 'center' }}>BACS</th>
            <th style={{ padding: '6px', textAlign: 'center' }}>Décret Tertiaire</th>
            <th style={{ padding: '6px', textAlign: 'center' }}>ISO 50001</th>
          </tr>
        </thead>
        <tbody>
          {concerned.map((it, i) => (
            <tr key={it.usage_id || i} style={{ borderBottom: '1px solid #f3f4f6' }}>
              <td style={{ padding: '6px', fontWeight: it.is_significant ? 600 : 400 }}>
                {it.label}
              </td>
              <td style={{ padding: '6px', textAlign: 'center' }}>
                {it.concerned_by_bacs ? (
                  it.bacs_covered ? (
                    <span style={{ color: '#16a34a', fontWeight: 600 }}>Couvert</span>
                  ) : (
                    <span style={{ color: '#dc2626', fontWeight: 600 }}>Manquant</span>
                  )
                ) : (
                  <span style={{ color: '#9ca3af' }}>—</span>
                )}
              </td>
              <td style={{ padding: '6px', textAlign: 'center' }}>
                {it.concerned_by_dt ? (
                  <span style={{ color: '#d97706', fontWeight: 600 }}>Concerné</span>
                ) : (
                  <span style={{ color: '#9ca3af' }}>—</span>
                )}
              </td>
              <td style={{ padding: '6px', textAlign: 'center' }}>
                {it.concerned_by_iso50001 ? (
                  <span style={{ color: '#2563eb', fontWeight: 600 }}>UES</span>
                ) : (
                  <span style={{ color: '#9ca3af' }}>—</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Risque principal */}
      {top_risk && (
        <div
          style={{
            marginTop: 10,
            padding: '8px 12px',
            background: '#fff7ed',
            border: '1px solid #fed7aa',
            borderRadius: 6,
            fontSize: 12,
            color: '#9a3412',
          }}
        >
          Principal risque : {top_risk}
        </div>
      )}

      {/* CTA */}
      <button
        onClick={() => navigate('/conformite/tertiaire')}
        style={{
          marginTop: 10,
          padding: '6px 14px',
          fontSize: 12,
          borderRadius: 6,
          border: '1px solid #d1d5db',
          background: 'white',
          cursor: 'pointer',
          fontWeight: 500,
        }}
      >
        Voir la conformité détaillée →
      </button>
    </div>
  );
}

// ── V1.2: Liens Facture / Contrat / Achat ────────────────────────────────

function BillingLinksWidget({ billing, cost, navigate }) {
  if (!billing) return null;

  const priceSource = billing.price_ref?.source;
  const hasContract = !!billing.contract;
  const hasInvoices = billing.invoices_summary?.count > 0;

  // Message contextuel sur la source du calcul de coût
  const costSourceMsg = hasContract
    ? 'Prix du contrat actif'
    : priceSource === 'facture'
      ? 'Prix moyen issu des factures'
      : 'Prix par défaut (aucune facture ni contrat)';

  return (
    <div>
      {/* Source de calcul explicite */}
      <div
        style={{
          fontSize: 12,
          color: '#6b7280',
          marginBottom: 10,
          padding: '6px 10px',
          background: '#f9fafb',
          borderRadius: 6,
          borderLeft: '3px solid #3b82f6',
        }}
      >
        Base de calcul du coût : <strong>{costSourceMsg}</strong>
        {!hasContract && priceSource === 'facture' && (
          <span style={{ color: '#d97706', marginLeft: 8 }}>
            — Rattacher un contrat pour un calcul plus précis
          </span>
        )}
      </div>

      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 14 }}>
        {/* Prix de référence */}
        <div
          style={{
            flex: '1 1 180px',
            padding: '12px 16px',
            background: '#f9fafb',
            borderRadius: 8,
          }}
        >
          <div style={{ fontSize: 11, color: '#6b7280' }}>Prix de référence</div>
          <div style={{ fontSize: 20, fontWeight: 700 }}>
            {fmt(billing.price_ref?.value * 100, 2)}{' '}
            <span style={{ fontSize: 12, fontWeight: 400 }}>c€/kWh</span>
          </div>
          <DataSourceBadge
            source={
              priceSource === 'contrat'
                ? 'mesure_directe'
                : priceSource === 'facture'
                  ? 'facturation'
                  : 'estimation_prorata'
            }
          />
          <span style={{ fontSize: 10, color: '#9ca3af', marginLeft: 6 }}>
            {priceSourceLabel(priceSource)}
          </span>
        </div>

        {/* Contrat actif */}
        {hasContract ? (
          <div
            style={{
              flex: '1 1 220px',
              padding: '12px 16px',
              background: '#f0fdf4',
              borderRadius: 8,
              border: '1px solid #bbf7d0',
            }}
          >
            <div style={{ fontSize: 11, color: '#6b7280' }}>Contrat actif</div>
            <div style={{ fontSize: 14, fontWeight: 600 }}>{billing.contract.supplier}</div>
            <div style={{ fontSize: 11, color: '#6b7280' }}>
              {billing.contract.tariff_option || '—'} · Fin : {billing.contract.end_date || '—'}
            </div>
          </div>
        ) : (
          <div
            style={{
              flex: '1 1 220px',
              padding: '12px 16px',
              background: hasInvoices ? '#fffbeb' : '#fef2f2',
              borderRadius: 8,
              border: `1px solid ${hasInvoices ? '#fde68a' : '#fecaca'}`,
            }}
          >
            <div style={{ fontSize: 11, color: hasInvoices ? '#92400e' : '#991b1b' }}>
              Aucun contrat rattaché
            </div>
            <div style={{ fontSize: 12, color: '#6b7280' }}>
              {hasInvoices
                ? 'Le coût utilise le prix moyen des factures importées'
                : 'Le coût utilise un prix de référence par défaut'}
            </div>
          </div>
        )}

        {/* Factures */}
        {billing.invoices_summary && (
          <div
            style={{
              flex: '1 1 180px',
              padding: '12px 16px',
              background: '#f9fafb',
              borderRadius: 8,
            }}
          >
            <div style={{ fontSize: 11, color: '#6b7280' }}>Factures 12 mois</div>
            <div style={{ fontSize: 20, fontWeight: 700 }}>
              {fmt(billing.invoices_summary.total_eur)}{' '}
              <span style={{ fontSize: 12, fontWeight: 400 }}>EUR</span>
            </div>
            <div style={{ fontSize: 11, color: '#6b7280' }}>
              {billing.invoices_summary.count} facture(s) ·{' '}
              {fmt(billing.invoices_summary.total_kwh)} kWh
            </div>
          </div>
        )}
      </div>

      {/* Liens rapides — contextuels */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {hasInvoices && (
          <button
            onClick={() => navigate(billing.links?.bill_intel || '/bill-intel')}
            style={{
              padding: '5px 12px',
              fontSize: 12,
              borderRadius: 6,
              border: '1px solid #e5e7eb',
              background: 'white',
              cursor: 'pointer',
              fontWeight: 500,
              display: 'flex',
              alignItems: 'center',
              gap: 5,
            }}
          >
            💰 Voir les factures →
          </button>
        )}
        <button
          onClick={() => navigate(billing.links?.contract_radar || '/contrats-radar')}
          style={{
            padding: '5px 12px',
            fontSize: 12,
            borderRadius: 6,
            border: '1px solid #e5e7eb',
            background: 'white',
            cursor: 'pointer',
            fontWeight: 500,
            display: 'flex',
            alignItems: 'center',
            gap: 5,
          }}
        >
          📄 {hasContract ? 'Explorer le contrat' : 'Rattacher un contrat'} →
        </button>
        <button
          onClick={() => navigate(billing.links?.purchase || '/achat-energie')}
          style={{
            padding: '5px 12px',
            fontSize: 12,
            borderRadius: 6,
            border: '1px solid #e5e7eb',
            background: 'white',
            cursor: 'pointer',
            fontWeight: 500,
            display: 'flex',
            alignItems: 'center',
            gap: 5,
          }}
        >
          📈 Scénarios d&apos;achat →
        </button>
      </div>
    </div>
  );
}

// ── Main Page ────────────────────────────────────────────────────────────

export default function UsagesDashboardPage() {
  const { selectedSiteId, scopedSites } = useScope();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();
  const printRef = useRef(null);

  const siteId = selectedSiteId;
  const siteName = scopedSites?.find((s) => s.id === siteId)?.nom;

  useEffect(() => {
    if (!siteId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    getUsagesDashboard(siteId)
      .then(setData)
      .catch((err) => setError(err?.response?.data?.detail || err.message))
      .finally(() => setLoading(false));
  }, [siteId]);

  const handleExport = () => {
    window.print();
  };

  if (!siteId) {
    return (
      <div style={{ padding: 32, textAlign: 'center', color: '#6b7280' }}>
        <h2>Usages Énergétiques</h2>
        <p>Sélectionnez un site pour afficher le tableau de bord des usages.</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div style={{ padding: 32, textAlign: 'center' }}>
        <div style={{ fontSize: 14, color: '#6b7280' }}>Chargement des usages...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: 32 }}>
        <div style={{ padding: 16, background: '#fee2e2', borderRadius: 8, color: '#991b1b' }}>
          Erreur : {error}
        </div>
      </div>
    );
  }

  if (!data) return null;

  const {
    readiness,
    metering_plan,
    top_ues,
    cost_breakdown,
    active_drifts,
    baselines,
    compliance,
    billing_links,
    summary,
  } = data;

  return (
    <div ref={printRef} style={{ padding: '24px 32px', maxWidth: 1100, margin: '0 auto' }}>
      {/* Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 20,
        }}
      >
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: '#111827', margin: 0 }}>
            Usages Énergétiques
          </h1>
          <p style={{ fontSize: 13, color: '#6b7280', margin: '4px 0 0' }}>
            Usage → Dérive → Action → Gain → Preuve → Conformité → Facture
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <ReadinessBadge score={readiness.score} level={readiness.level} />
          <button
            onClick={handleExport}
            className="print-hide"
            style={{
              padding: '6px 14px',
              fontSize: 12,
              borderRadius: 6,
              border: '1px solid #d1d5db',
              background: 'white',
              cursor: 'pointer',
              fontWeight: 500,
            }}
          >
            Exporter / Imprimer
          </button>
        </div>
      </div>

      {/* KPI Row */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
        <KpiCard label="Conso totale" value={fmt(summary.total_kwh)} unit="kWh/an" />
        <KpiCard label="Coût total" value={fmt(summary.total_eur)} unit="EUR/an" />
        <KpiCard
          label="Sous-compteurs"
          value={summary.sub_meters_count}
          sub={
            summary.sub_meters_count > 0
              ? `${summary.metering_coverage_pct ?? 0}% couverture`
              : 'Non installés'
          }
        />
        <KpiCard
          label="UES mesurés"
          value={`${summary.measured_ues ?? 0}/${summary.ues_count ?? 0}`}
          sub={summary.estimated_ues > 0 ? `${summary.estimated_ues} estimé(s)` : 'Tous mesurés'}
        />
        <KpiCard label="Dérives actives" value={summary.active_drifts_count} />
        <KpiCard
          label="Prix réf."
          value={fmt(billing_links?.price_ref?.value * 100, 1)}
          unit="c€/kWh"
          sub={priceSourceLabel(summary.price_source)}
        />
      </div>

      {/* Recommandations readiness */}
      {readiness.recommendations && readiness.recommendations.length > 0 && (
        <div
          style={{
            ...sectionStyle,
            background: '#fffbeb',
            border: '1px solid #fde68a',
            padding: '12px 18px',
          }}
        >
          <div style={{ fontSize: 13, fontWeight: 600, color: '#92400e', marginBottom: 6 }}>
            Actions pour améliorer la readiness :
          </div>
          <ul style={{ margin: 0, paddingLeft: 20, fontSize: 12, color: '#78350f' }}>
            {readiness.recommendations.map((r, i) => (
              <li key={i} style={{ marginBottom: 3 }}>
                {r}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* V1.2: Baseline / Avant-Après */}
      <div style={sectionStyle}>
        <h2 style={h2Style}>Baseline & Avant/Après</h2>
        <p style={{ fontSize: 12, color: '#6b7280', margin: '0 0 10px' }}>
          Comparaison N-1 (baseline) vs N (actuel) pour les usages avec sous-compteurs. Écarts et
          tendances calculés automatiquement.
        </p>
        <BaselineTable baselines={baselines} />
      </div>

      {/* Top UES */}
      <div style={sectionStyle}>
        <h2 style={h2Style}>Usages Énergétiques Significatifs (UES)</h2>
        <UesTable ues={top_ues} />
      </div>

      {/* Plan de comptage */}
      <div style={sectionStyle}>
        <h2 style={h2Style}>Plan de comptage</h2>
        <MeteringPlanTree plan={metering_plan} />
      </div>

      {/* Dérives prioritaires */}
      <div style={sectionStyle}>
        <h2 style={h2Style}>Dérives prioritaires</h2>
        <DriftCards drifts={active_drifts} navigate={navigate} />
      </div>

      {/* V1.2: Widget conformité par usage */}
      <div style={sectionStyle}>
        <h2 style={h2Style}>Impact conformité</h2>
        <p style={{ fontSize: 12, color: '#6b7280', margin: '0 0 10px' }}>
          Couverture des usages par BACS, Décret Tertiaire et critères ISO 50001.
        </p>
        <ComplianceWidget compliance={compliance} navigate={navigate} />
      </div>

      {/* Coût par usage */}
      <div style={sectionStyle}>
        <h2 style={h2Style}>Coût par usage</h2>
        <CostBreakdown cost={cost_breakdown} />
      </div>

      {/* V1.2: Liens facture / contrat / achat */}
      <div style={sectionStyle}>
        <h2 style={h2Style}>Impact facture & achat</h2>
        <BillingLinksWidget billing={billing_links} cost={cost_breakdown} navigate={navigate} />
      </div>

      {/* Liens cross-brique */}
      <div className="print-hide" style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
        {[
          { label: 'Diagnostic', route: '/diagnostic-conso', icon: '🔍' },
          { label: 'Conformité', route: '/conformite/tertiaire', icon: '📋' },
          { label: 'Factures', route: '/bill-intel', icon: '💰' },
          { label: 'Actions', route: '/actions', icon: '🎯' },
          { label: 'Patrimoine', route: '/patrimoine', icon: '🏢' },
        ].map((link) => (
          <button
            key={link.route}
            onClick={() => navigate(link.route)}
            style={{
              flex: '1 1 160px',
              padding: '12px 16px',
              background: 'white',
              border: '1px solid #e5e7eb',
              borderRadius: 10,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              fontSize: 13,
              fontWeight: 500,
              color: '#374151',
            }}
          >
            <span style={{ fontSize: 18 }}>{link.icon}</span>
            {link.label}
            <span style={{ marginLeft: 'auto', color: '#9ca3af' }}>→</span>
          </button>
        ))}
      </div>

      {/* Print styles */}
      <style>{`
        @media print {
          .print-hide { display: none !important; }
          body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
        }
      `}</style>
    </div>
  );
}
