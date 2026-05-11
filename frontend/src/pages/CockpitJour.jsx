/**
 * PROMEOS — CockpitJour (Sprint Grammaire v1.2 / Phase 3.4 V2 Hub Page L11)
 *
 * Page Hub L11 « Briefing du jour » — composition pure des primitifs canoniques
 * grammar/hub/* sur le payload `/api/cockpit/jour` (5 helpers backend).
 *
 * Doctrine PROMEOS Sol v1.1 + addendum L11 :
 *   - L11.1 SolHeroPremiumNight : eyebrow + titre Fraunces + meta SCM
 *   - L11.2 KpiTriptych (3 KPI) + ChartPair (2 ChartFrame)
 *   - L11.3 Highlights (3 a 5 HubHighlight differencies — anti AP3)
 *   - L11.5 HubPageFooter (Source · Confiance · MAJ)
 *
 * Aucun calcul metier ici (regle d'or PROMEOS) : tous les libelles, valeurs,
 * deltas, footScm sont fournis par le backend via _build_cockpit_jour_*.
 *
 * Filtres temporels : useFilter() (period/view/sort) — re-fetch automatique
 * a chaque changement de period.
 *
 * Tracabilite : `data-page="cockpit-jour"` + `data-doctrine="L11"` au root,
 * exploite par le source-guard CI hub-page-uses-canonical-grammar.
 */
import { useEffect, useMemo, useState } from 'react';
import {
  HubPage,
  SolHeroPremiumNight,
  ChartFrame,
  HubHighlight,
  HubPageFooter,
  HubKpiCard,
} from '../components/grammar';
import { useFilter } from '../contexts/FilterContext';
import { getCockpitJour } from '../services/api';
import { logger } from '../services/logger';

const TAG = 'CockpitJour';

// Phase F.1 — KpiTriptychCard inline supprime, remplace par <HubKpiCard>
// (primitif grammar/hub/HubKpiCard.jsx). Cf docs/audits/phase_3_4_phase_e_decision.md
// et ADR-021 section "Extraction trail".

/**
 * BarsDaily7d — Petit chart SVG 7 barres (S/D/L/M/M/J/V) tone-aware.
 * Pas de Recharts (overhead inutile pour 7 barres statiques HELIOS demo).
 */
function BarsDaily7d({ series = [] }) {
  if (!series.length) return null;
  const max = Math.max(...series.map((d) => d.value || 0), 1);
  const width = 100; // pct
  const barW = 100 / series.length - 3;
  const toneFill = {
    crit: 'var(--sol-refuse-line)',
    warn: 'var(--sol-attention-line)',
    pos: 'var(--sol-succes-line)',
    neutral: 'var(--sol-ink-300)',
  };

  return (
    <svg
      role="img"
      aria-label="Consommation 7 jours en MWh"
      viewBox="0 0 100 60"
      preserveAspectRatio="none"
      style={{ width: `${width}%`, height: '120px' }}
    >
      {series.map((d, i) => {
        const h = (d.value / max) * 50;
        const x = i * (barW + 3);
        const fill = toneFill[d.tone] || toneFill.neutral;
        return (
          <g key={`bar-${i}`}>
            <rect x={x} y={55 - h} width={barW} height={h} fill={fill} rx="0.5">
              <title>
                {d.day} : {d.value} MWh
              </title>
            </rect>
            <text
              x={x + barW / 2}
              y={59}
              textAnchor="middle"
              fontSize="3.5"
              fill="var(--sol-ink-500)"
              fontFamily="var(--sol-font-mono)"
            >
              {d.day}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

/**
 * LineCharge24h — Petit chart SVG courbe 24h vs souscrite (HELIOS demo).
 * Profil HP/HC simule (creux 0h-6h, plateau jour, pic 18h-20h).
 * Pas de Recharts — courbe statique fait foi pour la demo.
 */
function LineCharge24h({ subscribedKw = 1500 }) {
  const hours = Array.from({ length: 25 }, (_, i) => i);
  const fakePower = (h) => {
    if (h < 6) return 60 + Math.sin(h * 0.6) * 10;
    if (h < 9) return 80 + (h - 6) * 8;
    if (h < 12) return 105 + Math.sin(h * 0.4) * 5;
    if (h < 14) return 95 + Math.sin(h * 0.7) * 4;
    if (h < 18) return 100 + Math.cos(h * 0.3) * 6;
    if (h < 21) return 115 + Math.sin((h - 18) * 1.1) * 6;
    return 75 + Math.sin(h * 0.5) * 8;
  };
  const points = hours.map(
    (h) => `${(h / 24) * 100},${60 - (fakePower(h) / subscribedKw) * 60 * 4}`
  );
  // Limit y to plot range — clamp negative
  const safePoints = points.map((p) => {
    const [x, y] = p.split(',').map(Number);
    return `${x},${Math.max(2, Math.min(58, y))}`;
  });

  return (
    <svg
      role="img"
      aria-label="Courbe de charge 24h vs puissance souscrite"
      viewBox="0 0 100 60"
      preserveAspectRatio="none"
      style={{ width: '100%', height: '120px' }}
    >
      {/* Grid lignes */}
      <line x1="0" y1="15" x2="100" y2="15" stroke="var(--sol-ink-200)" strokeWidth="0.2" />
      <line x1="0" y1="30" x2="100" y2="30" stroke="var(--sol-ink-200)" strokeWidth="0.2" />
      <line x1="0" y1="45" x2="100" y2="45" stroke="var(--sol-ink-200)" strokeWidth="0.2" />

      {/* Ligne souscrite (top, en haut hors champ — afficher repere) */}
      <line
        x1="0"
        y1="3"
        x2="100"
        y2="3"
        stroke="var(--sol-refuse-line)"
        strokeWidth="0.4"
        strokeDasharray="1.5,1.5"
      />
      <text
        x="0"
        y="2"
        fontSize="2.5"
        fill="var(--sol-refuse-fg)"
        fontFamily="var(--sol-font-mono)"
      >
        Souscrite {subscribedKw} kW
      </text>

      {/* Courbe consommation */}
      <polyline
        points={safePoints.join(' ')}
        fill="none"
        stroke="var(--sol-hch-fg)"
        strokeWidth="0.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* Labels heures */}
      <text x="0" y="59" fontSize="2.8" fill="var(--sol-ink-500)" fontFamily="var(--sol-font-mono)">
        0h
      </text>
      <text
        x="48"
        y="59"
        fontSize="2.8"
        fill="var(--sol-ink-500)"
        fontFamily="var(--sol-font-mono)"
        textAnchor="middle"
      >
        12h
      </text>
      <text
        x="100"
        y="59"
        fontSize="2.8"
        fill="var(--sol-ink-500)"
        fontFamily="var(--sol-font-mono)"
        textAnchor="end"
      >
        24h
      </text>
    </svg>
  );
}

/**
 * Skeleton de chargement — preserve la structure 1 hero + 3 KPI + 2 charts + 3 highlights
 * pour eviter le shift de layout au mount.
 */
function CockpitJourSkeleton() {
  const skel = (h) => (
    <div
      className="rounded-xl"
      style={{ background: 'var(--sol-ink-100)', height: `${h}px` }}
      aria-hidden="true"
    />
  );
  return (
    <main
      data-page="cockpit-jour"
      data-doctrine="L11"
      data-state="loading"
      className="max-w-[1180px] mx-auto px-7 py-6 animate-pulse"
    >
      {skel(180)}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5 mt-5">
        {skel(128)}
        {skel(128)}
        {skel(128)}
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5 mt-5">
        {skel(220)}
        {skel(220)}
      </div>
      <div className="space-y-2 mt-5">
        {skel(70)}
        {skel(70)}
        {skel(70)}
      </div>
    </main>
  );
}

/**
 * ErrorBlock — message minimaliste si fetch echoue (pas une page d'erreur globale,
 * juste un fallback in-place coherent avec la grammaire Sol).
 */
function ErrorBlock({ onRetry }) {
  return (
    <main
      data-page="cockpit-jour"
      data-doctrine="L11"
      data-state="error"
      className="max-w-[1180px] mx-auto px-7 py-6"
    >
      <div
        className="rounded-xl border p-6"
        style={{
          background: 'var(--sol-refuse-bg)',
          borderColor: 'var(--sol-refuse-line)',
          color: 'var(--sol-refuse-fg)',
        }}
      >
        <h2
          style={{
            fontFamily: 'var(--sol-font-display)',
            fontSize: '20px',
            fontWeight: 500,
            margin: '0 0 6px 0',
          }}
        >
          Le briefing du jour est temporairement indisponible.
        </h2>
        <p style={{ fontSize: '13px', margin: '0 0 12px 0' }}>
          Source EMS · vérifier la connectivité backend ou réessayer dans quelques instants.
        </p>
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="font-mono"
            style={{
              fontSize: '12px',
              padding: '6px 12px',
              borderRadius: '7px',
              background: 'white',
              color: 'var(--sol-refuse-fg)',
              border: '1px solid var(--sol-refuse-line)',
            }}
          >
            Réessayer
          </button>
        )}
      </div>
    </main>
  );
}

export default function CockpitJour() {
  const { period } = useFilter();
  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch — re-trigger on period change (L11 filter mecanism)
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getCockpitJour({ period })
      .then((data) => {
        if (cancelled) return;
        setPayload(data);
      })
      .catch((err) => {
        if (cancelled) return;
        logger.warn(TAG, 'fetch /cockpit/jour failed', err);
        setError(err);
        setPayload(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [period]);

  const retry = () => {
    setError(null);
    setLoading(true);
    getCockpitJour({ period })
      .then((data) => setPayload(data))
      .catch((err) => {
        logger.warn(TAG, 'retry /cockpit/jour failed', err);
        setError(err);
      })
      .finally(() => setLoading(false));
  };

  // --- Memoize children arrays AVANT les early-returns (regle React Hooks).
  // payload peut etre null pendant le loading initial — on derive les listes
  // en lectures defensives pour eviter les crashes au mount.
  const kpis = payload?.kpis ?? [];
  const charts = payload?.charts ?? [];
  const highlights = payload?.highlights ?? [];

  const kpiChildren = useMemo(
    () => kpis.slice(0, 3).map((kpi) => <HubKpiCard key={kpi.id} kpi={kpi} />),
    [kpis]
  );

  const chartChildren = useMemo(() => {
    const out = [];
    const bar = charts.find((c) => c.type === 'bar_daily_7d');
    const cdc = charts.find((c) => c.type === 'line_24h_hp_hc');
    if (bar) {
      out.push(
        <ChartFrame
          key={bar.id}
          question={bar.question}
          answer={bar.answer}
          source={bar.footScm || {}}
        >
          <BarsDaily7d series={bar.series || []} />
        </ChartFrame>
      );
    }
    if (cdc) {
      out.push(
        <ChartFrame
          key={cdc.id}
          question={cdc.question}
          answer={cdc.answer}
          source={cdc.footScm || {}}
        >
          <LineCharge24h subscribedKw={cdc.subscribed_kw} />
        </ChartFrame>
      );
    }
    return out;
  }, [charts]);

  const highlightChildren = useMemo(
    () =>
      highlights
        .slice(0, 5)
        .map((h) => (
          <HubHighlight
            key={h.id}
            rang={h.rang}
            severity={h.severity}
            category={h.category}
            scope={h.scope}
            title={h.title}
            evidence={h.evidence}
            impact={h.impact}
            invitation={h.invitation}
          />
        )),
    [highlights]
  );

  // --- Loading / Error gates (apres les hooks pour respecter l'ordre React) ---
  if (loading && !payload) return <CockpitJourSkeleton />;
  if (error && !payload) return <ErrorBlock onRetry={retry} />;
  if (!payload) return null;

  const { hero, footer = {} } = payload;

  // Marqueurs source-guard `data-page="cockpit-jour"` + `data-doctrine="L11"` :
  // poses sur le skeleton/error fallbacks (ci-dessus) et repris ici sur un wrapper
  // <div> conteneur (HubPage est strict-props, ne forward pas les data-*).
  return (
    <div data-page="cockpit-jour" data-doctrine="L11">
      <HubPage pillar="briefing">
        {/* L11.1 — Hero premium-night */}
        <SolHeroPremiumNight
          eyebrow={hero?.eyebrow}
          title={hero?.title}
          sub={hero?.sub}
          meta={hero?.meta}
          alerts={hero?.alerts}
          primaryCta={{ label: 'Voir le centre d’action', href: '/anomalies' }}
        />

        {/* L11.2 — Triptyque KPI (exactement 3) */}
        <HubPage.KpiTriptych>{kpiChildren}</HubPage.KpiTriptych>

        {/* L11.2 — Paire chart (exactement 2) */}
        <HubPage.ChartPair>{chartChildren}</HubPage.ChartPair>

        {/* L11.3 — Highlights (3 a 5) */}
        <HubPage.Highlights title="Top 3 priorités du jour" linkAll="/anomalies">
          {highlightChildren}
        </HubPage.Highlights>

        {/* L11.5 — Footer SCM */}
        <HubPageFooter
          source={(footer.sources || []).map((s) => s.label).join(' · ')}
          confidence={footer.confidence}
          updatedAt={footer.updatedAt}
          methodologyUrl={footer.methodologyHref}
        />
      </HubPage>
    </div>
  );
}
