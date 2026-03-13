/**
 * PROMEOS — Page Usages Énergétiques V1.1
 * Page pivot : Readiness + Plan de comptage + Top UES + Dérives + Coût par usage
 *
 * Route : /usages
 */
import React, { useEffect, useState, useContext } from 'react';
import { ScopeContext } from '../contexts/ScopeContext';
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
    import_csv: '#1e40af',
    gtb_api: '#6d28d9',
    facturation: '#0e7490',
  })[src] || '#6b7280';

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

function UesTable({ ues, onAction }) {
  if (!ues || ues.length === 0) {
    return (
      <p style={{ color: '#9ca3af', fontStyle: 'italic' }}>Aucun usage significatif détecté.</p>
    );
  }
  return (
    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
      <thead>
        <tr style={{ borderBottom: '2px solid #e5e7eb', textAlign: 'left' }}>
          <th style={{ padding: '8px 6px' }}>Usage</th>
          <th style={{ padding: '8px 6px', textAlign: 'right' }}>kWh/an</th>
          <th style={{ padding: '8px 6px', textAlign: 'right' }}>%</th>
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
  );
}

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

// ── Main Page ────────────────────────────────────────────────────────────

export default function UsagesDashboardPage() {
  const { selectedSite } = useContext(ScopeContext);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const siteId = selectedSite?.id;

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

  const { readiness, metering_plan, top_ues, cost_breakdown, active_drifts, summary } = data;

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

  return (
    <div style={{ padding: '24px 32px', maxWidth: 1100, margin: '0 auto' }}>
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
            Vue pivot : patrimoine, usages, dérives, coût, conformité
          </p>
        </div>
        <ReadinessBadge score={readiness.score} level={readiness.level} />
      </div>

      {/* KPI Row */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
        <KpiCard label="Conso totale" value={fmt(summary.total_kwh)} unit="kWh/an" />
        <KpiCard label="Coût total" value={fmt(summary.total_eur)} unit="EUR/an" />
        <KpiCard
          label="Readiness"
          value={summary.readiness_score}
          unit="/100"
          sub={summary.readiness_level}
        />
        <KpiCard label="Sous-compteurs" value={summary.sub_meters_count} />
        <KpiCard label="Dérives actives" value={summary.active_drifts_count} />
        <KpiCard label="UES identifiés" value={summary.ues_count} />
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

      {/* Plan de comptage */}
      <div style={sectionStyle}>
        <h2 style={h2Style}>Plan de comptage</h2>
        <MeteringPlanTree plan={metering_plan} />
      </div>

      {/* Top UES */}
      <div style={sectionStyle}>
        <h2 style={h2Style}>Répartition par usage (Top UES)</h2>
        <UesTable ues={top_ues} />
      </div>

      {/* Dérives prioritaires */}
      <div style={sectionStyle}>
        <h2 style={h2Style}>Dérives prioritaires</h2>
        <DriftCards drifts={active_drifts} navigate={navigate} />
      </div>

      {/* Coût par usage */}
      <div style={sectionStyle}>
        <h2 style={h2Style}>Coût par usage</h2>
        <CostBreakdown cost={cost_breakdown} />
      </div>

      {/* Liens cross-brique */}
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
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
    </div>
  );
}
