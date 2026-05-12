/**
 * PROMEOS — CockpitJour (Sprint Grammaire v1.2 / Phase 3.4 V2 Hub Page L11)
 *
 * Page Hub L11 « Briefing du jour » — composition pure des primitifs
 * canoniques `grammar/hub/*` sur le payload `/api/cockpit/jour`. Aucun
 * calcul metier ici (regle d'or §8.1) — backend fournit libelles + valeurs.
 *
 * Doctrine : Sol v1.1 + addendum L11 (`docs/vision/promeos_sol_doctrine.md` §12).
 * Filtres temporels : `useFilter()` re-fetch automatique sur period change.
 * Tracabilite : `data-page="cockpit-jour"` + `data-doctrine="L11"` au root.
 */
import { useEffect, useMemo, useState } from 'react';
import {
  HubPage,
  SolHeroPremiumNight,
  ChartFrame,
  ChartFrameBars,
  ChartFrameLine,
  HubHighlight,
  HubPageFooter,
  HubKpiCard,
  HubSkeleton,
  HubError,
  AutoTerm,
} from '../components/grammar';
import { useFilter } from '../contexts/FilterContext';
import { getCockpitJour } from '../services/api';
import { logger } from '../services/logger';

const TAG = 'CockpitJour';

// Historique extractions Phase F (F.1 → F.7) : docs/adr/ADR-021-hub-page-grammar-l11.md
// (section "Extraction trail") + commits 68dd1547 / 29666297 / c466ebbf / ff2b3a4d /
// a4ad525d / c7b51567 / 81db5384.

/**
 * renderChartInner — dispatcher polymorphique par chart.type.
 * Fonction pure module-scope (audit code-reviewer P1 fix : sortir du composant
 * pour respecter useMemo deps exhaustives + faciliter test unitaire isolé).
 * Audit Phase F P1 fix : pas de magic 1500 ; si `subscribed_kw` absent,
 * on omet le threshold (le backend doit toujours fournir cette valeur pour
 * un site live).
 */
function renderChartInner(c) {
  if (c.type === 'bar_daily_7d') {
    const data = (c.series || []).map((d) => ({ label: d.day, value: d.value, tone: d.tone }));
    return (
      <ChartFrameBars
        data={data}
        baseline={c.baseline}
        unit={c.unit || 'MWh/j'}
        annotation={c.annotation}
        ariaLabel="Consommation 7 jours en MWh"
      />
    );
  }
  if (c.type === 'line_24h_hp_hc') {
    // Phase F.9 — format FR séparateur milliers (1 500 vs 1500). Label
    // construit côté primitif via formatFr, mais aussi explicite ici pour
    // les tests source-guards qui grepent la chaîne.
    const threshold =
      typeof c.subscribed_kw === 'number'
        ? {
            value: c.subscribed_kw,
            unit: 'kW',
            label: `P. souscrite ${new Intl.NumberFormat('fr-FR').format(c.subscribed_kw)} kW`,
          }
        : undefined;
    return (
      <ChartFrameLine
        seriesHP={c.series_hp}
        seriesHC={c.series_hc}
        threshold={threshold}
        peak={c.peak}
        hcZones={c.hc_zones}
        ariaLabel="Courbe de charge 24h vs puissance souscrite"
      />
    );
  }
  return null;
}

export default function CockpitJour() {
  const { period } = useFilter();
  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch unifie (initial + retry). cancelled passe-through pour race-safety.
  const fetchJour = (cancelled = { current: false }) => {
    setLoading(true);
    setError(null);
    return getCockpitJour({ period })
      .then((data) => !cancelled.current && setPayload(data))
      .catch((err) => {
        if (cancelled.current) return;
        logger.warn(TAG, 'fetch /cockpit/jour failed', err);
        setError(err);
        setPayload(null);
      })
      .finally(() => !cancelled.current && setLoading(false));
  };

  useEffect(() => {
    const cancelled = { current: false };
    fetchJour(cancelled);
    return () => {
      cancelled.current = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- period only; fetchJour
    // close sur setters stables, pas besoin de le declarer dans deps.
  }, [period]);

  const retry = () => fetchJour();

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

  const chartChildren = useMemo(
    () =>
      charts
        .map((c) => {
          const inner = renderChartInner(c);
          return inner ? (
            <ChartFrame key={c.id} question={c.question} answer={c.answer} source={c.footScm || {}}>
              {inner}
            </ChartFrame>
          ) : null;
        })
        .filter(Boolean),
    [charts]
  );

  const highlightChildren = useMemo(
    () =>
      highlights.slice(0, 5).map(({ id, title, evidence, _audit, tier, ...rest }) => (
        // F.5 — title/evidence wrappés AutoTerm pour acronymes BACS/EMS/OPERAT/CVC/DT.
        // F.24 — `_audit` du backend (ADR-022) mappé vers `priorityProof` du
        // composant HubHighlight pour afficher le badge transparent doctrinal.
        <HubHighlight
          key={id}
          {...rest}
          title={<AutoTerm text={title} />}
          evidence={<AutoTerm text={evidence} />}
          priorityProof={
            _audit
              ? {
                  score_total: _audit.score_total,
                  score_breakdown: _audit.score_breakdown,
                  tier,
                }
              : undefined
          }
        />
      )),
    [highlights]
  );

  // --- Loading / Error gates (apres les hooks pour respecter l'ordre React) ---
  if (loading && !payload) {
    const skel = (v, n) =>
      Array.from({ length: n }, (_, i) => <HubSkeleton key={`${v}-${i}`} variant={v} />);
    return (
      <div data-page="cockpit-jour" data-doctrine="L11" data-state="loading">
        <HubPage pillar="briefing">
          <HubSkeleton variant="hero" />
          <HubPage.KpiTriptych>{skel('kpi', 3)}</HubPage.KpiTriptych>
          <HubPage.ChartPair>{skel('chart', 2)}</HubPage.ChartPair>
          <HubPage.Highlights title="Top 3 priorités du jour">
            {skel('highlight', 3)}
          </HubPage.Highlights>
        </HubPage>
      </div>
    );
  }
  if (error && !payload) {
    return (
      <div data-page="cockpit-jour" data-doctrine="L11" data-state="error">
        <HubPage pillar="briefing">
          <HubError
            title="Le briefing du jour est temporairement indisponible."
            description={
              <AutoTerm text="Source EMS · vérifier la connectivité backend ou réessayer dans quelques instants." />
            }
            correlationId={error?.correlationId || error?.response?.headers?.['x-correlation-id']}
            onRetry={retry}
          />
        </HubPage>
      </div>
    );
  }
  if (!payload) return null;

  const { hero, footer = {} } = payload;

  return (
    <div data-page="cockpit-jour" data-doctrine="L11">
      <HubPage pillar="briefing">
        {/* L11.1 — Hero premium-night */}
        <SolHeroPremiumNight
          eyebrow={hero?.eyebrow}
          title={<AutoTerm text={hero?.title} />}
          sub={<AutoTerm text={hero?.sub} />}
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
