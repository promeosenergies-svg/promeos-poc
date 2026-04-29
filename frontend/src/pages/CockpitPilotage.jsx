/**
 * CockpitPilotage — Page Pilotage refonte WOW (29/04/2026).
 *
 * Audience : energy manager · 30 s · « quoi traiter aujourd'hui »
 * Doctrine §11.3 : page de pilotage, source unique partagée avec Synthèse stratégique
 *
 * Cible : `docs/maquettes/cockpit-sol2/cockpit-pilotage-briefing-jour.html`
 *
 * Sections (top → bottom) :
 *   1. Header : kicker + switch éditorial + H1 Fraunces + sous-ligne mono
 *   2. Pills alertes + bouton Centre d'action
 *   3. Triptyque KPI temporel multi-échelle (Conso J-1 / Conso mois vs N-1 DJU / Pic kW)
 *   4. 2 visuels glanceables (Conso 7 jours barres + Courbe charge J-1 HP/HC)
 *   5. File de traitement P1-P5 priorisée par impact
 *   6. Footer source/confiance/MAJ/méthodologie
 *
 * Sources data :
 *   - useCockpitFacts('current_month') → triptyque + alertes + footer
 *   - getCockpitPriorities() → file P1-P5
 */
import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Bell, ArrowRight } from 'lucide-react';

import useCockpitFacts from '../hooks/useCockpitFacts';
import SolKickerWithSwitch from '../ui/sol/SolKickerWithSwitch';
import { getCockpitPriorities } from '../services/api/cockpit';
import { useScope } from '../contexts/ScopeContext';

const FR_DATE = new Intl.DateTimeFormat('fr-FR', {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
});

function fmtMwh(v) {
  if (v == null || !Number.isFinite(v)) return '—';
  return v.toFixed(1).replace('.', ',');
}

function fmtKw(v) {
  if (v == null || !Number.isFinite(v)) return '—';
  return Math.round(v).toLocaleString('fr-FR');
}

function fmtPct(v, withSign = true) {
  if (v == null || !Number.isFinite(v)) return '—';
  const sign = v > 0 ? '+ ' : v < 0 ? '− ' : '';
  return `${withSign ? sign : ''}${Math.abs(Math.round(v))} %`;
}

function deltaSeverity(deltaPct) {
  if (deltaPct == null || !Number.isFinite(deltaPct)) return 'neutral';
  const abs = Math.abs(deltaPct);
  if (abs < 5) return 'neutral';
  if (abs < 15) return 'warning';
  return 'danger';
}

const SEVERITY_TONE = {
  neutral: { fg: 'var(--sol-ink-700)' },
  warning: { fg: 'var(--sol-attention-fg)' },
  danger: { fg: 'var(--sol-refuse-fg)' },
};

const URGENCY_TONE = {
  critical: {
    bg: 'var(--sol-refuse-bg)',
    line: 'var(--sol-refuse-line)',
    fg: 'var(--sol-refuse-fg)',
    label: 'Critique',
  },
  high: {
    bg: 'var(--sol-attention-bg)',
    line: 'var(--sol-attention-line)',
    fg: 'var(--sol-attention-fg)',
    label: 'Important',
  },
  medium: {
    bg: 'var(--sol-attention-bg)',
    line: 'var(--sol-attention-line)',
    fg: 'var(--sol-attention-fg)',
    label: 'À surveiller',
  },
  low: {
    bg: 'var(--sol-bg-canvas)',
    line: 'var(--sol-rule)',
    fg: 'var(--sol-ink-700)',
    label: 'Information',
  },
};

function urgencyTone(u) {
  return URGENCY_TONE[u] || URGENCY_TONE.medium;
}

// ── Triptyque KPI temporel multi-échelle ─────────────────────────────

function KpiCard({ label, tooltip, value, unit, deltaText, deltaSev, hint }) {
  const tone = SEVERITY_TONE[deltaSev || 'neutral'];
  return (
    <div className="rounded-lg p-4" style={{ background: 'var(--sol-bg-canvas)' }}>
      <div
        className="font-mono uppercase tracking-[0.07em] text-[11px] mb-1.5"
        style={{ color: 'var(--sol-ink-500)' }}
      >
        {label}
        {tooltip && (
          <span
            tabIndex={0}
            title={tooltip}
            aria-label={tooltip}
            className="ml-1 cursor-help"
            style={{ borderBottom: '1px dotted var(--sol-ink-400)' }}
          >
            ?
          </span>
        )}
      </div>
      <div className="flex items-baseline gap-2 flex-wrap">
        <div
          style={{
            fontFamily: 'var(--sol-font-display)',
            fontSize: '28px',
            fontWeight: 500,
            lineHeight: 1,
            color: 'var(--sol-ink-900)',
          }}
        >
          {value}
          {unit && (
            <span className="ml-1" style={{ fontSize: '14px', color: 'var(--sol-ink-700)' }}>
              {unit}
            </span>
          )}
        </div>
        {deltaText && (
          <div className="text-xs font-medium" style={{ color: tone.fg }}>
            {deltaText}
          </div>
        )}
      </div>
      {hint && (
        <div
          className="mt-1.5 font-mono uppercase tracking-[0.07em]"
          style={{
            fontSize: '10.5px',
            color: 'var(--sol-ink-500)',
          }}
        >
          {hint}
        </div>
      )}
    </div>
  );
}

function KpiTriptyqueEnergetique({ facts }) {
  const c = facts?.consumption || {};
  const p = facts?.power || {};
  const monthly = c.monthly_vs_n1 || {};

  // KPI 1 — Conso J-1 court terme (baseline historique)
  const jm1 = c.j_minus_1_mwh;
  const baseJm1 = c.baseline_j_minus_1?.value_mwh;
  const deltaJm1 = c.baseline_j_minus_1?.delta_pct;

  // KPI 2 — Conso mois courant DJU-ajusté (moyen terme)
  const monthlyMwh = monthly.current_month_mwh;
  const monthlyDeltaPct = monthly.delta_pct_dju_adjusted;
  const monthlyTooltip = monthly.current_month_label
    ? `${monthly.current_month_label} vs N-1 normalisé · Baseline ${monthly.baseline_method?.replace(/_/g, ' ') || '—'}${monthly.r_squared ? ` · r² ${monthly.r_squared.toFixed(2)}` : ''}${monthly.calibration_date ? ` · calibrée ${new Date(monthly.calibration_date).toLocaleDateString('fr-FR')}` : ''}`
    : 'Comparaison mois courant vs N-1 DJU-ajustée';

  // KPI 3 — Pic puissance J-1 contractuel
  const peakKw = p.peak_j_minus_1_kw;
  const subscribedKw = p.subscribed_kw;
  const peakDeltaPct = p.delta_pct;
  const peakTime = p.peak_time;

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5 my-4">
      <KpiCard
        label="Conso J−1 · groupe"
        tooltip="Baseline A · moyenne mêmes jours sur 12 semaines · confiance haute"
        value={fmtMwh(jm1)}
        unit="MWh"
        deltaText={baseJm1 != null && deltaJm1 != null ? `${fmtPct(deltaJm1)} vs baseline` : null}
        deltaSev={deltaSeverity(deltaJm1)}
        hint={baseJm1 != null ? `Réf. ${fmtMwh(baseJm1)} MWh · même jour S−1` : null}
      />
      <KpiCard
        label="Conso mois courant"
        tooltip={monthlyTooltip}
        value={monthlyMwh != null ? Math.round(monthlyMwh).toLocaleString('fr-FR') : '—'}
        unit="MWh"
        deltaText={
          monthlyDeltaPct != null
            ? `${fmtPct(monthlyDeltaPct)} vs ${monthly.current_month_label?.match(/(\w+ \d{4})/g)?.[0]?.replace(/\d{4}/, (y) => +y - 1) || 'N−1'}`
            : null
        }
        deltaSev={deltaSeverity(monthlyDeltaPct)}
        hint={monthly.current_month_label ? `DJU-ajusté · ${monthly.current_month_label}` : null}
      />
      <KpiCard
        label="Pic puissance J−1"
        tooltip="Mesure CDC 30 min agrégée sites · vs puissance souscrite contractuelle"
        value={fmtKw(peakKw)}
        unit="kW"
        deltaText={
          peakDeltaPct != null && peakDeltaPct !== 0 ? `${fmtPct(peakDeltaPct)} vs souscrite` : null
        }
        deltaSev={deltaSeverity(peakDeltaPct)}
        hint={
          subscribedKw != null
            ? `Souscrite ${fmtKw(subscribedKw)} kW${peakTime && peakTime !== '00:00' ? ` · ${peakTime}` : ''}`
            : null
        }
      />
    </div>
  );
}

// ── Visuels glanceables (V1 placeholders SVG structurés) ─────────────

function ConsoSevenDaysBars() {
  // V1 : structure SVG fidèle maquette, valeurs placeholder.
  // V2 : alimenté par /api/cockpit/timeseries?period=7d (Étape 4 backend gap-filler).
  return (
    <div
      className="rounded-md p-4"
      style={{
        background: 'var(--sol-bg-paper)',
        border: '0.5px solid var(--sol-rule)',
      }}
    >
      <div className="flex justify-between items-start gap-2 mb-2">
        <div>
          <div
            className="font-mono uppercase tracking-[0.07em] mb-1"
            style={{ fontSize: '11px', color: 'var(--sol-ink-500)' }}
          >
            Conso 7 jours · MWh/jour
          </div>
          <div className="text-xs" style={{ color: 'var(--sol-ink-700)', lineHeight: 1.4 }}>
            Visuel glanceable — données en cours de connexion timeseries.
          </div>
        </div>
        <Link
          to="/consommations/portfolio"
          className="text-[11px] font-mono uppercase tracking-[0.05em] no-underline shrink-0"
          style={{ color: 'var(--sol-ink-500)' }}
        >
          Détail →
        </Link>
      </div>
      <svg
        viewBox="0 0 320 130"
        xmlns="http://www.w3.org/2000/svg"
        style={{ width: '100%', height: 'auto', display: 'block', marginTop: 6 }}
        role="img"
        aria-label="Barres consommation 7 jours, samedi en rouge anomalie"
      >
        <line
          x1="32"
          y1="20"
          x2="320"
          y2="20"
          stroke="currentColor"
          strokeOpacity=".08"
          strokeDasharray="2,3"
        />
        <line
          x1="32"
          y1="55"
          x2="320"
          y2="55"
          stroke="currentColor"
          strokeOpacity=".08"
          strokeDasharray="2,3"
        />
        <line
          x1="32"
          y1="90"
          x2="320"
          y2="90"
          stroke="currentColor"
          strokeOpacity=".15"
          strokeDasharray="3,3"
        />
        <text
          x="28"
          y="23"
          textAnchor="end"
          fontFamily="var(--sol-font-mono)"
          fontSize="9"
          fill="currentColor"
          fillOpacity=".5"
        >
          12
        </text>
        <text
          x="28"
          y="58"
          textAnchor="end"
          fontFamily="var(--sol-font-mono)"
          fontSize="9"
          fill="currentColor"
          fillOpacity=".5"
        >
          8
        </text>
        <text
          x="28"
          y="93"
          textAnchor="end"
          fontFamily="var(--sol-font-mono)"
          fontSize="9"
          fill="currentColor"
          fillOpacity=".5"
        >
          4
        </text>
        <line
          x1="32"
          y1="68"
          x2="320"
          y2="68"
          stroke="currentColor"
          strokeOpacity=".25"
          strokeDasharray="2,2"
        />
        <g fill="var(--sol-calme-fg)">
          <rect x="42" y="48" width="32" height="55" rx="2" />
          <rect x="84" y="50" width="32" height="53" rx="2" />
          <rect x="126" y="44" width="32" height="59" rx="2" />
          <rect x="168" y="46" width="32" height="57" rx="2" />
          <rect x="210" y="49" width="32" height="54" rx="2" />
        </g>
        <rect x="252" y="22" width="32" height="81" rx="2" fill="var(--sol-refuse-fg)" />
        <rect
          x="294"
          y="55"
          width="22"
          height="48"
          rx="2"
          fill="var(--sol-calme-fg)"
          fillOpacity=".5"
        />
        <text
          x="266"
          y="14"
          textAnchor="middle"
          fontSize="9"
          fontWeight="500"
          fill="var(--sol-refuse-fg)"
        >
          + 39 %
        </text>
        <g
          fontFamily="var(--sol-font-mono)"
          fontSize="9"
          fill="currentColor"
          fillOpacity=".55"
          textAnchor="middle"
        >
          <text x="58" y="120">
            L
          </text>
          <text x="100" y="120">
            M
          </text>
          <text x="142" y="120">
            M
          </text>
          <text x="184" y="120">
            J
          </text>
          <text x="226" y="120">
            V
          </text>
          <text x="268" y="120" fontWeight="500" fill="var(--sol-refuse-fg)" fillOpacity="1">
            S
          </text>
          <text x="305" y="120">
            D
          </text>
        </g>
      </svg>
      <div
        className="mt-1.5 font-mono uppercase tracking-[0.07em]"
        style={{ fontSize: '10px', color: 'var(--sol-ink-500)' }}
      >
        Visuel cible · données live arrivent Étape 4
      </div>
    </div>
  );
}

function CourbeChargeJMinus1({ subscribedKw }) {
  return (
    <div
      className="rounded-md p-4"
      style={{
        background: 'var(--sol-bg-paper)',
        border: '0.5px solid var(--sol-rule)',
      }}
    >
      <div className="flex justify-between items-start gap-2 mb-2">
        <div>
          <div
            className="font-mono uppercase tracking-[0.07em] mb-1"
            style={{ fontSize: '11px', color: 'var(--sol-ink-500)' }}
          >
            Courbe de charge J−1 · groupe · kW
          </div>
          <div className="text-xs" style={{ color: 'var(--sol-ink-700)', lineHeight: 1.4 }}>
            HP / HC contractuelles · ligne souscrite{' '}
            <strong style={{ fontWeight: 500 }}>
              {subscribedKw != null ? `${fmtKw(subscribedKw)} kW` : '—'}
            </strong>
          </div>
        </div>
        <div className="flex gap-2 shrink-0">
          <span
            className="font-mono uppercase tracking-[0.05em] inline-flex items-center gap-1"
            style={{ fontSize: '10px', color: 'var(--sol-ink-500)' }}
          >
            <span
              className="inline-block"
              style={{
                width: 8,
                height: 2,
                background: 'var(--sol-hpe-fg)',
              }}
            />
            HP
          </span>
          <span
            className="font-mono uppercase tracking-[0.05em] inline-flex items-center gap-1"
            style={{ fontSize: '10px', color: 'var(--sol-ink-500)' }}
          >
            <span
              className="inline-block"
              style={{
                width: 8,
                height: 2,
                background: 'var(--sol-hch-fg)',
              }}
            />
            HC
          </span>
        </div>
      </div>
      <svg
        viewBox="0 0 320 130"
        xmlns="http://www.w3.org/2000/svg"
        style={{ width: '100%', height: 'auto', display: 'block', marginTop: 6 }}
        role="img"
        aria-label="Courbe de charge J moins 1 du groupe"
      >
        <defs>
          <linearGradient id="hp-fill-pilotage" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="var(--sol-hpe-fg)" stopOpacity=".18" />
            <stop offset="100%" stopColor="var(--sol-hpe-fg)" stopOpacity="0" />
          </linearGradient>
        </defs>
        <rect x="32" y="10" width="46" height="95" fill="var(--sol-hch-fg)" fillOpacity=".05" />
        <rect x="284" y="10" width="36" height="95" fill="var(--sol-hch-fg)" fillOpacity=".05" />
        <line
          x1="32"
          y1="20"
          x2="320"
          y2="20"
          stroke="currentColor"
          strokeOpacity=".08"
          strokeDasharray="2,3"
        />
        <line
          x1="32"
          y1="55"
          x2="320"
          y2="55"
          stroke="currentColor"
          strokeOpacity=".08"
          strokeDasharray="2,3"
        />
        <line
          x1="32"
          y1="90"
          x2="320"
          y2="90"
          stroke="currentColor"
          strokeOpacity=".15"
          strokeDasharray="3,3"
        />
        <line
          x1="32"
          y1="34"
          x2="320"
          y2="34"
          stroke="var(--sol-refuse-fg)"
          strokeOpacity=".55"
          strokeDasharray="3,3"
          strokeWidth="1"
        />
        <text
          x="318"
          y="31"
          textAnchor="end"
          fontFamily="var(--sol-font-mono)"
          fontSize="8.5"
          fill="var(--sol-refuse-fg)"
          fillOpacity=".85"
        >
          P. souscrite {subscribedKw != null ? `${fmtKw(subscribedKw)}` : '—'} kW
        </text>
        <path
          d="M32,90 L78,80 L92,68 L106,46 L120,40 L134,42 L148,52 L162,58 L176,52 L190,46 L204,42 L218,46 L232,50 L246,56 L260,64 L274,76 L284,82 L284,105 L32,105 Z"
          fill="url(#hp-fill-pilotage)"
          fillOpacity=".7"
        />
        <path
          d="M32,92 L48,90 L60,88 L72,84 L78,80"
          fill="none"
          stroke="var(--sol-hch-fg)"
          strokeWidth="1.6"
        />
        <path
          d="M78,80 L92,68 L106,46 L120,40 L134,42 L148,52 L162,58 L176,52 L190,46 L204,42 L218,46 L232,50 L246,56 L260,64 L274,76 L284,82"
          fill="none"
          stroke="var(--sol-hpe-fg)"
          strokeWidth="1.6"
        />
        <path
          d="M284,82 L296,86 L308,90 L320,93"
          fill="none"
          stroke="var(--sol-hch-fg)"
          strokeWidth="1.6"
        />
        <g
          fontFamily="var(--sol-font-mono)"
          fontSize="9"
          fill="currentColor"
          fillOpacity=".55"
          textAnchor="middle"
        >
          <text x="32" y="120">
            0 h
          </text>
          <text x="106" y="120">
            8 h
          </text>
          <text x="176" y="120">
            12 h
          </text>
          <text x="250" y="120">
            18 h
          </text>
          <text x="320" y="120">
            22 h
          </text>
        </g>
      </svg>
      <div
        className="mt-1.5 font-mono uppercase tracking-[0.07em]"
        style={{ fontSize: '10px', color: 'var(--sol-ink-500)' }}
      >
        Visuel cible · données CDC live arrivent Étape 4
      </div>
    </div>
  );
}

// ── File de traitement P1-P5 ─────────────────────────────────────────

function FileTraitementRow({ rank, item }) {
  const tone = urgencyTone(item.urgency);
  return (
    <Link
      to={item.action_url || '/anomalies'}
      className="block no-underline"
      style={{
        background: tone.bg,
        border: `0.5px solid ${tone.line}`,
        borderRadius: 8,
        padding: '11px 13px',
        marginBottom: 5,
        color: 'var(--sol-ink-900)',
        transition: 'transform 0.15s, box-shadow 0.15s',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.transform = 'translateX(2px)';
        e.currentTarget.style.boxShadow = '0 1px 3px rgba(0,0,0,0.06)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = 'translateX(0)';
        e.currentTarget.style.boxShadow = 'none';
      }}
    >
      <div className="grid items-center gap-3" style={{ gridTemplateColumns: '36px 1fr auto' }}>
        <span
          className="font-mono font-medium text-center px-2 py-0.5 rounded"
          style={{
            background: 'rgba(0,0,0,0.06)',
            color: tone.fg,
            fontSize: 10.5,
            letterSpacing: '0.05em',
            textTransform: 'uppercase',
          }}
        >
          P{rank}
        </span>
        <div className="min-w-0">
          <div className="font-medium mb-0.5" style={{ fontSize: 14, color: 'var(--sol-ink-900)' }}>
            {item.title}
          </div>
          <div
            className="flex items-center gap-2 flex-wrap"
            style={{ fontSize: 11.5, color: 'var(--sol-ink-700)' }}
          >
            <span
              className="font-mono uppercase tracking-[0.05em]"
              style={{ fontSize: 10, color: 'var(--sol-ink-500)' }}
            >
              {item.domain}
            </span>
            {item.urgency && (
              <span
                className="inline-flex items-center px-1.5 py-0.5 rounded font-mono uppercase tracking-[0.05em]"
                style={{
                  fontSize: 9.5,
                  background: 'rgba(0,0,0,0.06)',
                  color: tone.fg,
                  fontWeight: 500,
                }}
              >
                {tone.label}
              </span>
            )}
          </div>
        </div>
        <ArrowRight size={14} style={{ color: tone.fg, opacity: 0.6 }} aria-hidden="true" />
      </div>
    </Link>
  );
}

function FileTraitement({ priorities, loading }) {
  if (loading) {
    return (
      <div
        className="font-mono uppercase tracking-[0.07em]"
        style={{ fontSize: 11, color: 'var(--sol-ink-500)' }}
      >
        Chargement priorités…
      </div>
    );
  }
  if (!priorities?.length) {
    return (
      <div
        className="rounded-md p-4 text-center"
        style={{
          background: 'var(--sol-succes-bg)',
          border: '0.5px solid var(--sol-succes-line)',
          color: 'var(--sol-succes-fg)',
        }}
      >
        <strong style={{ fontWeight: 500 }}>Tout est sous contrôle aujourd'hui.</strong> Aucune
        priorité critique sur le portefeuille.
      </div>
    );
  }
  return (
    <div>
      <div className="flex justify-between items-center mb-2">
        <div
          className="font-mono uppercase tracking-[0.07em]"
          style={{ fontSize: 11, color: 'var(--sol-ink-500)' }}
        >
          File de traitement · {priorities.length} ligne
          {priorities.length > 1 ? 's' : ''} priorisée
          {priorities.length > 1 ? 's' : ''}
        </div>
        <div
          className="font-mono uppercase tracking-[0.07em]"
          style={{ fontSize: 10.5, color: 'var(--sol-ink-500)' }}
        >
          Tri urgence · domaine ↓
        </div>
      </div>
      {priorities.map((p) => (
        <FileTraitementRow key={`${p.rank}-${p.title}`} rank={p.rank} item={p} />
      ))}
    </div>
  );
}

// ── Page racine ──────────────────────────────────────────────────────

export default function CockpitPilotage() {
  const navigate = useNavigate();
  const { facts, loading: factsLoading } = useCockpitFacts('current_month');
  const { org } = useScope();
  const [priorities, setPriorities] = useState(null);
  const [prioritiesLoading, setPrioritiesLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setPrioritiesLoading(true);
    getCockpitPriorities()
      .then((data) => {
        if (!cancelled) setPriorities(data?.priorities || []);
      })
      .catch(() => {
        if (!cancelled) setPriorities([]);
      })
      .finally(() => {
        if (!cancelled) setPrioritiesLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const sitesCount = facts?.scope?.site_count ?? org?.sites_count ?? 0;
  const orgName = facts?.scope?.org_name || org?.name || '';
  const dataQualityPct = facts?.data_quality?.data_completeness_pct;
  const lastUpdate = facts?.metadata?.last_update;
  const sources = facts?.metadata?.sources || [];
  const confidence = facts?.metadata?.confidence;

  const today = new Date();
  const todayLabel = FR_DATE.format(today);
  const weekIso = (() => {
    // ISO week — fallback simple
    const d = new Date(today);
    d.setHours(0, 0, 0, 0);
    d.setDate(d.getDate() + 4 - (d.getDay() || 7));
    const yearStart = new Date(d.getFullYear(), 0, 1);
    return Math.ceil(((d - yearStart) / 86400000 + 1) / 7);
  })();

  const lastUpdateRel = lastUpdate
    ? (() => {
        const diffMin = Math.round((Date.now() - new Date(lastUpdate).getTime()) / 60000);
        if (diffMin < 60) return `il y a ${diffMin} min`;
        const h = Math.round(diffMin / 60);
        return `il y a ${h} h`;
      })()
    : '—';

  const alertsTotal = facts?.alerts?.total ?? 0;
  const criticalCount = facts?.alerts?.by_severity?.critical ?? 0;

  const scopeLabel = `${orgName}${sitesCount ? ` — ${sitesCount} sites` : ''}`;

  return (
    <div
      className="max-w-[1280px] mx-auto"
      style={{
        background: 'var(--sol-bg-paper)',
        borderRadius: 12,
        border: '0.5px solid var(--sol-rule)',
        padding: '1.4rem 1.6rem 1.2rem',
      }}
    >
      {/* Header — kicker + switch + H1 + sous-ligne + pills droite */}
      <div className="flex justify-between items-start gap-3.5 flex-wrap">
        <div className="flex-1 min-w-[260px]">
          <SolKickerWithSwitch scope={`Cockpit · ${scopeLabel}`} currentRoute="jour" />
          <h1
            className="mt-1.5 mb-1"
            style={{
              fontFamily: 'var(--sol-font-display)',
              fontSize: 24,
              fontWeight: 500,
              lineHeight: 1.2,
              color: 'var(--sol-ink-900)',
            }}
          >
            Bonjour — voici ce qui mérite votre attention{' '}
            <em
              style={{
                fontStyle: 'italic',
                color: 'var(--sol-ink-700)',
                fontWeight: 400,
              }}
            >
              · {todayLabel}
            </em>
          </h1>
          <div
            className="mt-1 font-mono uppercase tracking-[0.07em]"
            style={{ fontSize: 11, color: 'var(--sol-ink-500)' }}
          >
            Données EMS {lastUpdateRel}
            {dataQualityPct != null ? ` · qualité ${dataQualityPct} %` : ''}
            {' · semaine '}
            {weekIso}
          </div>
        </div>
        <div className="flex gap-1.5 flex-wrap items-center">
          {alertsTotal > 0 && (
            <span
              className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full font-mono uppercase tracking-[0.04em]"
              style={{
                fontSize: 11,
                border: '0.5px solid var(--sol-rule)',
                color: 'var(--sol-ink-700)',
                background: 'var(--sol-bg-paper)',
              }}
            >
              <span
                className="inline-block rounded-full"
                style={{
                  width: 6,
                  height: 6,
                  background:
                    criticalCount > 0 ? 'var(--sol-refuse-fg)' : 'var(--sol-attention-fg)',
                }}
              />
              {alertsTotal} alerte{alertsTotal > 1 ? 's' : ''}
            </span>
          )}
          <button
            type="button"
            onClick={() => navigate('/anomalies?status=open')}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md font-medium transition-colors"
            style={{
              fontSize: 13,
              border: '0.5px solid var(--sol-ink-300)',
              background: 'var(--sol-bg-paper)',
              color: 'var(--sol-ink-900)',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'var(--sol-bg-canvas)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'var(--sol-bg-paper)';
            }}
          >
            <Bell size={14} aria-hidden="true" />
            Centre d'action
            <ArrowRight size={12} aria-hidden="true" style={{ opacity: 0.6 }} />
          </button>
        </div>
      </div>

      {/* Triptyque KPI temporel multi-échelle */}
      {factsLoading && !facts ? (
        <div
          className="my-4 font-mono uppercase tracking-[0.07em] text-center py-8"
          style={{ fontSize: 11, color: 'var(--sol-ink-500)' }}
        >
          Chargement KPI…
        </div>
      ) : (
        <KpiTriptyqueEnergetique facts={facts} />
      )}

      {/* 2 visuels glanceables */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 mb-4">
        <ConsoSevenDaysBars />
        <CourbeChargeJMinus1 subscribedKw={facts?.power?.subscribed_kw} />
      </div>

      {/* File de traitement */}
      <div className="mb-4">
        <FileTraitement priorities={priorities} loading={prioritiesLoading} />
      </div>

      {/* Footer Sol */}
      <div
        className="flex justify-between flex-wrap gap-2.5 pt-3"
        style={{ borderTop: '0.5px solid var(--sol-rule)' }}
      >
        <div
          className="font-mono uppercase tracking-[0.07em]"
          style={{ fontSize: 11, color: 'var(--sol-ink-500)' }}
        >
          Source {sources.join(' + ') || 'PROMEOS'}
          {confidence ? ` · confiance ${confidence}` : ''}
          {' · mis à jour '}
          {lastUpdateRel} ·{' '}
          <Link
            to="/methodologie/cockpit"
            className="no-underline"
            style={{
              color: 'var(--sol-ink-500)',
              borderBottom: '0.5px dotted var(--sol-ink-400)',
            }}
          >
            méthodologie
          </Link>
        </div>
      </div>
    </div>
  );
}
