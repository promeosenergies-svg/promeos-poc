/**
 * pages/CockpitStrategique — Synthèse Stratégique data-driven (Phase 3.5 D.5).
 *
 * Page polymorphique consommant payload.strategic_mode (ADR-023 §1).
 * From scratch : AUCUN import de pages/Cockpit.jsx, composition pure grammar/hub/*.
 * Persona DG/COMEX défaut, période défaut = month.
 */

import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  CadreApplicable,
  ChartFrame,
  ChartFrameBenchSites,
  ChartFrameTrajectoryLine,
  DossierP1,
  HubKpiCard,
  HubPage,
  HubPageFooter,
  SolHeroPremiumNight,
  StrategicModeBanner,
  VerdictFinal,
} from '../components/grammar/hub';
import { useFilter } from '../contexts/FilterContext';
import { usePersona } from '../contexts/PersonaContext';
import { getCockpitStrategique } from '../services/api';
import logger from '../utils/logger';

const TAG = '[CockpitStrategique]';

export default function CockpitStrategique() {
  const { period } = useFilter();
  const { persona, setDataQualityPct } = usePersona();
  const [searchParams] = useSearchParams();
  const legacyMode = searchParams.get('legacy') === '1';

  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (legacyMode) return; // page legacy rendu ailleurs (Cockpit.jsx)
    setLoading(true);
    setError(null);
    getCockpitStrategique({ period, persona })
      .then((data) => {
        setPayload(data);
        const quality = data?.hero?.meta?.quality_pct;
        if (typeof quality === 'number' && setDataQualityPct) {
          setDataQualityPct(quality);
        }
      })
      .catch((err) => {
        logger?.warn?.(TAG, 'fetch /cockpit/strategique failed', err);
        setError(err);
      })
      .finally(() => setLoading(false));
  }, [period, persona, legacyMode, setDataQualityPct]);

  if (legacyMode) {
    return <LegacyRedirectStub />;
  }

  if (loading || !payload) {
    return (
      <div data-page="cockpit-strategique" data-doctrine="L11" data-state="loading" className="p-6">
        <p style={{ fontFamily: 'var(--sol-font-mono, monospace)', fontSize: '12px' }}>
          Chargement de la Synthèse Stratégique…
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div data-page="cockpit-strategique" data-doctrine="L11" data-state="error" className="p-6">
        <p>Impossible de charger la Synthèse Stratégique. Réessayer ?</p>
      </div>
    );
  }

  const mode = payload.strategic_mode;
  return (
    <div
      data-page="cockpit-strategique"
      data-doctrine="L11"
      data-mode={mode}
      data-from-scratch="phase3.5"
    >
      <StrategicModeBanner mode={mode} />

      <HubPage pillar="strategique">
        <SolHeroPremiumNight
          eyebrow={payload.hero?.kicker}
          title={payload.hero?.title}
          sub={payload.hero?.sub_constat}
          meta={payload.hero?.meta}
        />

        <CadreApplicable
          applicability={payload.applicability}
          maturity={payload.patrimoine_maturity}
        />

        <HubPage.KpiTriptych>
          {(payload.kpis || []).map((k) => (
            <HubKpiCard key={k.id} {...k} />
          ))}
        </HubPage.KpiTriptych>

        <HubPage.ChartPair>{(payload.charts || []).map((c) => renderChart(c))}</HubPage.ChartPair>

        {payload.dossier_p1 && <DossierP1 {...payload.dossier_p1} />}

        <VerdictFinal {...(payload.verdict || {})} />

        <HubPageFooter {...(payload.footer || {})} />
      </HubPage>
    </div>
  );
}

function renderChart(c) {
  switch (c.type) {
    case 'trajectory_line':
      return (
        <ChartFrameTrajectoryLine
          key={c.id}
          question={c.question}
          answer={c.answer}
          data={c.data}
          footScm={c.foot_scm}
        />
      );
    case 'bench_sites':
      return (
        <ChartFrameBenchSites
          key={c.id}
          question={c.question}
          answer={c.answer}
          data={c.data}
          footScm={c.foot_scm}
        />
      );
    default:
      return (
        <ChartFrame key={c.id} question={c.question} answer={c.answer} footScm={c.foot_scm}>
          {c.type === 'bars_horizontal' || c.type === 'missing_list' ? (
            <SimpleBars data={c.data} />
          ) : (
            <RadarStub data={c.data} />
          )}
        </ChartFrame>
      );
  }
}

function SimpleBars({ data = [] }) {
  if (!Array.isArray(data) || data.length === 0) return null;
  const maxKey =
    data[0].pct !== undefined
      ? 'pct'
      : data[0].impact_keur_an !== undefined
        ? 'impact_keur_an'
        : 'rank';
  const max = Math.max(...data.map((d) => d[maxKey] || 0), 1);
  return (
    <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
      {data.map((row, idx) => (
        <li key={idx} className="flex items-center gap-2 py-1" style={{ fontSize: '12.5px' }}>
          <span style={{ flex: '0 0 140px' }}>{row.label || row.name || row.field}</span>
          <span
            style={{
              flex: 1,
              height: '14px',
              background: 'var(--sol-ink-100, #F2EDE5)',
              borderRadius: '7px',
              position: 'relative',
            }}
          >
            <span
              style={{
                display: 'block',
                height: '100%',
                width: `${((row[maxKey] || 0) / max) * 100}%`,
                background: 'var(--sol-ink-500, #7A6E5C)',
                borderRadius: '7px',
              }}
            />
          </span>
          <span
            style={{
              flex: '0 0 90px',
              textAlign: 'right',
              fontFamily: 'var(--sol-font-mono, monospace)',
            }}
          >
            {row.pct
              ? `${row.pct} %`
              : row.impact_keur_an
                ? `${row.impact_keur_an} k€`
                : `#${row.rank}`}
          </span>
        </li>
      ))}
    </ul>
  );
}

function RadarStub({ data = [] }) {
  return (
    <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
      {(Array.isArray(data) ? data : []).map((row, idx) => (
        <li key={idx} className="flex items-center gap-2 py-1" style={{ fontSize: '12.5px' }}>
          <span style={{ flex: 1 }}>{row.axis}</span>
          <span style={{ fontFamily: 'var(--sol-font-mono, monospace)' }}>{row.pct} %</span>
        </li>
      ))}
    </ul>
  );
}

function LegacyRedirectStub() {
  return (
    <div
      data-page="cockpit-strategique"
      data-state="legacy"
      style={{
        padding: '40px',
        fontFamily: 'var(--sol-font-mono, monospace)',
        fontSize: '13px',
        color: 'var(--sol-ink-700, #3D362C)',
      }}
    >
      Mode legacy demandé via <code>?legacy=1</code> — page Cockpit héritée accessible séparément.
      Cf. doc/dev/cockpit_legacy_deprecation.md.
    </div>
  );
}
