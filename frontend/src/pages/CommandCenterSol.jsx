/**
 * PROMEOS — CommandCenterSol (refonte from-scratch, route racine /)
 *
 * Persona : exploitant énergie multisite tertiaire.
 * Question répondue : « Qu'est-ce que je dois faire aujourd'hui ? »
 *
 * Doctrine appliquée :
 *   - AI-native : Sol prend la parole en hero (« Sol propose »).
 *   - Management by Exception : Top 3 priorités + Watchlist, pas de KPI décoratif.
 *   - T2V < 10 min : 6 sections ordonnées par criticité d'action.
 *
 * Structure :
 *   1. Header narratif Sol
 *   2. DeadlineBanner (urgence régulatoire)
 *   3. SolHero — proposition agentique du jour (depuis briefing[0])
 *   4. TodayActionsCard — top 5 priorités du jour
 *   5. SolLoadCurve — profil horaire J-1 + seuil 80% (discipline HP/HC)
 *   6. WatchlistCard — sites à surveiller
 *   7. Tuiles modules (accès aux 5 modules cross-stream)
 */
import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  SolPageHeader,
  SolHero,
  SolSectionHead,
  SolSourceChip,
  SolLoadCurve,
} from '../ui/sol';
import { useScope } from '../contexts/ScopeContext';
import {
  getActionsSummary,
  getNotificationsSummary,
  getNotificationsList,
  getComplianceBundle,
  getCockpit,
  getPatrimoineKpis,
  getSolProposal,
} from '../services/api';
import {
  NBSP,
  buildCommandKicker,
  buildCommandNarrative,
  buildCommandSubNarrative,
  computeStateIndex,
  formatFREur,
  freshness,
} from './command-center/sol_presenters';
import { buildFallbackLoadCurve } from './cockpit/sol_presenters';
import { SkeletonCard } from '../ui/Skeleton';
import { LayoutDashboard, ShieldCheck, Receipt, Building2, ShoppingCart } from 'lucide-react';
import {
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  CartesianGrid,
  ReferenceLine,
} from 'recharts';

// Refonte from-scratch : composants MAIN agentiques + builders
import DeadlineBanner from '../components/DeadlineBanner';
import TodayActionsCard from './cockpit/TodayActionsCard';
import WatchlistCard from './cockpit/WatchlistCard';
import { useCommandCenterData } from '../hooks/useCommandCenterData';
import { useCockpitData } from '../hooks/useCockpitData';
import {
  buildBriefing,
  buildWatchlist,
  buildTodayActions,
  buildOpportunities,
  checkConsistency,
} from '../models/dashboardEssentials';

// ──────────────────────────────────────────────────────────────────────────────

function useCommandData({ orgId } = {}) {
  const [state, setState] = useState({
    status: 'loading',
    actions: null,
    notifSummary: null,
    notifList: null,
    compliance: null,
    cockpit: null,
    patrimoine: null,
    solProposal: null,
  });

  useEffect(() => {
    let cancelled = false;
    setState((s) => ({ ...s, status: 'loading' }));

    Promise.allSettled([
      getActionsSummary(orgId).catch(() => null),
      getNotificationsSummary(orgId).catch(() => null),
      getNotificationsList({ org_id: orgId, limit: 10 }).catch(() => null),
      getComplianceBundle().catch(() => null),
      getCockpit().catch(() => null),
      getPatrimoineKpis().catch(() => null),
      getSolProposal().catch(() => null),
    ]).then(
      ([actions, notifSummary, notifList, compliance, cockpit, patrimoine, solProposal]) => {
        if (cancelled) return;
        setState({
          status: 'ready',
          actions: actions.status === 'fulfilled' ? actions.value : null,
          notifSummary: notifSummary.status === 'fulfilled' ? notifSummary.value : null,
          notifList: notifList.status === 'fulfilled' ? notifList.value : null,
          compliance: compliance.status === 'fulfilled' ? compliance.value : null,
          cockpit: cockpit.status === 'fulfilled' ? cockpit.value : null,
          patrimoine: patrimoine.status === 'fulfilled' ? patrimoine.value : null,
          solProposal: solProposal.status === 'fulfilled' ? solProposal.value : null,
        });
      }
    );

    return () => {
      cancelled = true;
    };
  }, [orgId]);

  return state;
}

// ──────────────────────────────────────────────────────────────────────────────

const MODULE_TILES = [
  {
    to: '/cockpit',
    label: 'Cockpit exécutif',
    desc: 'Synthèse portefeuille, KPIs 3 modes',
    Icon: LayoutDashboard,
  },
  {
    to: '/conformite',
    label: 'Conformité',
    desc: 'Décret tertiaire · BACS · APER',
    Icon: ShieldCheck,
  },
  { to: '/bill-intel', label: 'Facturation', desc: 'Shadow billing + anomalies', Icon: Receipt },
  { to: '/patrimoine', label: 'Patrimoine', desc: 'Sites · contrats · EUI', Icon: Building2 },
  {
    to: '/achat-energie',
    label: 'Achat énergie',
    desc: 'Arbitrage · scénarios · radar',
    Icon: ShoppingCart,
  },
];

const TILE_STYLE = {
  background: 'var(--sol-bg-paper)',
  border: '1px solid var(--sol-ink-200)',
  borderRadius: 8,
  padding: '16px 18px',
  cursor: 'pointer',
  textAlign: 'left',
  display: 'flex',
  alignItems: 'flex-start',
  gap: 12,
  transition: 'border-color 120ms, box-shadow 120ms',
};
const TILE_ICON_STYLE = { color: 'var(--sol-calme-fg)', flexShrink: 0, marginTop: 2 };
const TILE_BODY_STYLE = { flex: 1, minWidth: 0 };
const TILE_LABEL_STYLE = {
  fontFamily: 'var(--sol-font-body)',
  fontSize: 14,
  fontWeight: 600,
  color: 'var(--sol-ink-900)',
  marginBottom: 3,
};
const TILE_DESC_STYLE = { fontSize: 12, color: 'var(--sol-ink-500)', lineHeight: 1.4 };
const TILE_GRID_STYLE = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
  gap: 12,
  marginTop: 8,
};
const tileHoverEnter = (e) => {
  e.currentTarget.style.borderColor = 'var(--sol-calme-fg)';
  e.currentTarget.style.boxShadow = '0 2px 6px rgba(15, 23, 42, 0.06)';
};
const tileHoverLeave = (e) => {
  e.currentTarget.style.borderColor = 'var(--sol-ink-200)';
  e.currentTarget.style.boxShadow = '0 1px 2px rgba(15, 23, 42, 0.03)';
};

// ──────────────────────────────────────────────────────────────────────────────

function getRiskStatus(eur) {
  if (eur > 50000) return 'crit';
  if (eur > 10000) return 'warn';
  return 'ok';
}

// ──────────────────────────────────────────────────────────────────────────────

export default function CommandCenterSol() {
  const scopeCtx = useScope();
  const scope = scopeCtx?.scope || {};
  const scopedSites = scopeCtx?.scopedSites || [];
  const org = scopeCtx?.org;
  const scopeLabel = scopeCtx?.scopeLabel;
  const sitesCount = scopeCtx?.sitesCount;
  const orgName = org?.name || org?.label || scopeLabel || 'votre patrimoine';
  const navigate = useNavigate();

  const data = useCommandData({ orgId: scope.orgId });
  const cmd = useCommandCenterData();
  const kpisJ1 = cmd.kpisJ1 || {};
  const hourlyProfile = cmd.hourlyProfile || [];
  const weekSeries = cmd.weekSeries || [];
  const { kpis: cockpitKpis } = useCockpitData();

  // ─── Dérivations 7 jours + HP/HC J-1 ───────────────────────────────────────

  // 7 jours conso quotidienne — grille fixe de 7 jours (aujourd'hui-6 → aujourd'hui)
  // garantie même si le backend retourne moins. Jours sans data → kwh null + flag isMissing.
  // ATTENTION : on génère les dates en LOCAL (pas toISOString qui décale en UTC),
  // sinon mismatch avec le backend qui renvoie des dates UTC sans heure.
  const weekChartData = useMemo(() => {
    const dayFmt = new Intl.DateTimeFormat('fr-FR', { weekday: 'short', day: 'numeric' });
    const localDate = (d) => {
      const yyyy = d.getFullYear();
      const mm = String(d.getMonth() + 1).padStart(2, '0');
      const dd = String(d.getDate()).padStart(2, '0');
      return `${yyyy}-${mm}-${dd}`;
    };
    const today = new Date();
    const grid = [];
    for (let i = 6; i >= 0; i--) {
      const d = new Date(today);
      d.setDate(today.getDate() - i);
      grid.push({
        day: dayFmt.format(d).replace('.', ''),
        kwh: null,
        rawDate: localDate(d),
        isMissing: true,
      });
    }
    if (Array.isArray(weekSeries) && weekSeries.length > 0) {
      weekSeries.forEach((p) => {
        const idx = grid.findIndex((g) => g.rawDate === p.date);
        if (idx >= 0) {
          grid[idx].kwh = p.kwh;
          grid[idx].isMissing = p.kwh == null;
        }
      });
    }
    return grid;
  }, [weekSeries]);
  const weekAverage = useMemo(() => {
    const valid = weekChartData.filter((p) => p.kwh != null);
    if (valid.length === 0) return null;
    return Math.round(valid.reduce((s, p) => s + p.kwh, 0) / valid.length);
  }, [weekChartData]);
  const weekMissingCount = useMemo(
    () => weekChartData.filter((p) => p.isMissing).length,
    [weekChartData]
  );

  // Profil horaire 24h — données réelles si dispo, sinon fallback bureau type.
  // Robuste : seed HELIOS n'expose pas toujours d'agrégat horaire/30min, on garde
  // la signature visuelle (la SolLoadCurve est trop iconique pour être absente).
  // ATTENTION : on ajoute un point 24:00 (= dernière valeur) pour que la
  // bande HC droite (22→24h) ait un x2 ancrable côté Recharts.
  const loadCurveData = useMemo(() => {
    let data;
    if (Array.isArray(hourlyProfile) && hourlyProfile.length > 0) {
      data = hourlyProfile.map((p) => {
        const h = parseInt((p.heure || '0').replace('h', '').replace(':', ''), 10) || 0;
        return { time: `${String(h).padStart(2, '0')}:00`, value: p.kw };
      });
    } else {
      data = buildFallbackLoadCurve();
    }
    // Garantir un dernier point à 24:00 pour la bande HC droite
    if (data.length > 0 && data[data.length - 1].time !== '24:00') {
      const last = data[data.length - 1];
      data = [...data, { time: '24:00', value: last.value }];
    }
    return data;
  }, [hourlyProfile]);
  const loadCurveIsMock =
    !Array.isArray(hourlyProfile) || hourlyProfile.length === 0;

  // Pic dérivé de loadCurveData (uniformément, même en fallback)
  const peakPoint = useMemo(() => {
    if (!loadCurveData.length) return null;
    const max = loadCurveData.reduce(
      (m, p) => ((p.value ?? 0) > (m.value ?? 0) ? p : m),
      loadCurveData[0]
    );
    if (max?.value == null) return null;
    return {
      time: max.time,
      value: max.value,
      label: `pic ${max.time} · ${Math.round(max.value)} kW`,
    };
  }, [loadCurveData]);

  // HP/HC J-1 — ratio dérivé du profil horaire (HP = 06:00→22:00 standard).
  const hpcShare = useMemo(() => {
    if (!Array.isArray(loadCurveData) || loadCurveData.length === 0) return null;
    let hpKwh = 0;
    let hcKwh = 0;
    loadCurveData.forEach((p) => {
      const hour = parseInt((p.time || '00:00').split(':')[0], 10);
      const kw = Number(p.value) || 0;
      if (hour >= 6 && hour < 22) hpKwh += kw;
      else hcKwh += kw;
    });
    const total = hpKwh + hcKwh;
    if (total === 0) return null;
    const hpPct = Math.round((hpKwh / total) * 100);
    return {
      hpPct,
      hcPct: 100 - hpPct,
      hpKwh: Math.round(hpKwh),
      hcKwh: Math.round(hcKwh),
      totalKwh: Math.round(total),
    };
  }, [loadCurveData]);

  // ─── KPIs builder-ready (shape attendue par dashboardEssentials) ──────────

  const rawKpis = useMemo(() => {
    const total = scopedSites.length;
    const conformes = scopedSites.filter((s) => s.statut_conformite === 'conforme').length;
    const nonConformes = scopedSites.filter((s) => s.statut_conformite === 'non_conforme').length;
    const aRisque = scopedSites.filter((s) => s.statut_conformite === 'a_risque').length;
    const risque = scopedSites.reduce((sum, s) => sum + (s.risque_eur || 0), 0);
    const pctConf =
      cockpitKpis?.conformiteScore != null ? Math.round(cockpitKpis.conformiteScore) : 0;
    const couvertureDonnees =
      total > 0
        ? Math.round((scopedSites.filter((s) => s.conso_kwh_an > 0).length / total) * 100)
        : 0;
    const compStatus =
      nonConformes > 0 ? 'crit' : aRisque > 0 ? 'warn' : total > 0 ? 'ok' : 'neutral';
    return {
      total,
      conformes,
      nonConformes,
      aRisque,
      risque,
      pctConf,
      couvertureDonnees,
      compStatus,
      risqueStatus: getRiskStatus(risque),
    };
  }, [scopedSites, cockpitKpis]);

  const alertsCount =
    data.notifSummary?.total ?? data.notifSummary?.counts?.total ?? 0;

  const consistency = useMemo(() => checkConsistency(rawKpis), [rawKpis]);
  const watchlist = useMemo(
    () => buildWatchlist(rawKpis, scopedSites),
    [rawKpis, scopedSites]
  );
  const opportunities = useMemo(
    () => buildOpportunities(rawKpis, scopedSites),
    [rawKpis, scopedSites]
  );
  const briefing = useMemo(
    () => buildBriefing(rawKpis, watchlist, alertsCount),
    [rawKpis, watchlist, alertsCount]
  );
  const todayActions = useMemo(
    () => buildTodayActions(rawKpis, watchlist, opportunities),
    [rawKpis, watchlist, opportunities]
  );

  // ─── Présentation header (kicker, narrative existants) ────────────────────

  const kicker = buildCommandKicker({ scope: { orgName, sitesCount } });

  const actions = data.actions ?? {};
  const cockpitStats = data.cockpit?.stats ?? {};
  const compliance = data.compliance ?? {};
  const complianceScore = cockpitStats.compliance_score ?? compliance.compliance_score;
  const stateIndex = useMemo(
    () =>
      computeStateIndex({
        complianceScore,
        totalInvoices: data.cockpit?.billing?.total_invoices ?? 36,
        anomaliesCount: cockpitStats.alertes_actives ?? 0,
        activeSites: rawKpis.total,
        totalSites: rawKpis.total,
      }),
    [complianceScore, cockpitStats, rawKpis, data.cockpit]
  );
  const solActionsCount = actions.counts?.open ?? 0;
  const totalGain = actions.total_gain_eur ?? 0;
  const narrative = useMemo(
    () => buildCommandNarrative({ stateIndex, alertsCount, solActionsCount, totalGain }),
    [stateIndex, alertsCount, solActionsCount, totalGain]
  );
  const subNarrative = useMemo(() => buildCommandSubNarrative({ summary: actions }), [actions]);
  const dataFreshness = useMemo(
    () => freshness(data.cockpit?.stats?.compliance_computed_at),
    [data.cockpit]
  );

  // Sol proposition (top 1 du briefing — sert de hero agentique)
  const solTopProp = briefing[0];

  // ─── Rendu ───────────────────────────────────────────────────────────────

  if (data.status === 'loading') {
    return (
      <div>
        <SkeletonCard lines={1} />
        <SkeletonCard lines={3} />
        <SkeletonCard lines={5} />
      </div>
    );
  }

  return (
    <>
      <SolPageHeader
        kicker={kicker}
        title="Bonjour "
        titleEm="— vos actions du jour"
        narrative={narrative}
        subNarrative={subNarrative}
      />

      {/* 1. Urgence régulatoire (cross-vues canonique) */}
      <DeadlineBanner />

      {/* 2. SOL PROPOSE — hero agentique riche, alimenté par /api/sol/proposal.
          Backend retourne un plan d'action structuré (3 actions chiffrées avec
          impact €/an, délai, source module). Affiche le headline prescriptif +
          3 metrics (Actions / Gain potentiel / Délai) + liste actions chiffrées
          en panneau bottom. Fallback briefing[0] si endpoint indisponible. */}
      {(data.solProposal || solTopProp) && (
        <SolHero
          chip="Sol propose · plan d'action"
          title={data.solProposal?.headline || solTopProp?.label}
          description={
            data.solProposal
              ? `Sources : ${(data.solProposal.sources || []).join(' · ')} · scope ${data.solProposal.scope_label}`
              : briefing.length > 1
                ? `Sol a identifié ${briefing.length} priorités sur votre patrimoine.`
                : 'Plan d\'action prêt.'
          }
          metrics={[
            {
              label: 'Actions',
              value: `${data.solProposal?.actions?.length || todayActions.length || 0}`,
            },
            {
              label: 'Gain potentiel',
              value:
                data.solProposal?.total_impact_eur_per_year > 0
                  ? formatFREur(data.solProposal.total_impact_eur_per_year, 0)
                  : totalGain > 0
                    ? formatFREur(totalGain, 0)
                    : '—',
            },
            {
              label: 'Délai',
              value:
                data.solProposal?.actions?.[0]?.delay ||
                (solTopProp?.severity === 'critical'
                  ? 'aujourd\'hui'
                  : 'cette semaine'),
            },
          ]}
          actions={data.solProposal?.actions || []}
          onAction={(path) => path && navigate(path)}
          primaryLabel="Voir le plan complet"
          onPrimary={() => navigate('/actions')}
          secondaryLabel="Plus tard"
          onSecondary={() => {}}
        />
      )}

      {/* 3 + 5 — Top priorités & Watchlist pairés en grid 2-col
          (à faire / à surveiller, densités similaires, évite le vide horizontal).
          Children stretch via align-items default + cards full-height pour alignement parfait. */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))',
          gap: 16,
          alignItems: 'stretch',
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <SolSectionHead
            title="À traiter aujourd'hui"
            meta={
              todayActions.length > 0
                ? `${todayActions.length} priorité${todayActions.length > 1 ? 's' : ''} · ${dataFreshness}`
                : dataFreshness
            }
          />
          <div style={{ flex: 1, display: 'flex' }}>
            <div style={{ width: '100%' }}>
              <TodayActionsCard actions={todayActions} onNavigate={navigate} />
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <SolSectionHead
            title="À surveiller"
            meta={
              watchlist.length > 0
                ? `${watchlist.length} signal${watchlist.length > 1 ? 'aux' : ''}`
                : 'Tout va bien'
            }
          />
          <div style={{ flex: 1, display: 'flex' }}>
            <div style={{ width: '100%' }}>
              <WatchlistCard
                watchlist={watchlist}
                consistency={consistency}
                loading={false}
                onNavigate={navigate}
              />
            </div>
          </div>
        </div>
      </div>

      {/* 4. Activité 7 jours + Répartition HP/HC J-1 — grid 2-col, lectures complémentaires :
          tendance hebdo (semaine) + composition tarifaire (cost-optim). */}
      {(weekChartData.length > 0 || hpcShare) && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))',
            gap: 16,
            alignItems: 'stretch',
          }}
        >
          {/* Activité 7 jours */}
          {weekChartData.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <SolSectionHead
                title="Activité 7 derniers jours"
                meta={
                  weekAverage != null
                    ? `Moyenne ${weekAverage.toLocaleString('fr-FR')} kWh/jour${
                        weekMissingCount > 0
                          ? ` · ${weekMissingCount} jour${weekMissingCount > 1 ? 's' : ''} sans donnée`
                          : ''
                      }`
                    : weekMissingCount === 7
                      ? '7 jours sans donnée — raccordement en cours'
                      : 'Tendance hebdo · pas journalier'
                }
              />
              <div
                style={{
                  background: 'var(--sol-bg-paper)',
                  border: '1px solid var(--sol-ink-200)',
                  borderRadius: 8,
                  padding: 16,
                  flex: 1,
                  display: 'flex',
                  flexDirection: 'column',
                }}
              >
                <div style={{ width: '100%', height: 200, flex: 1, minHeight: 200 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={weekChartData}
                      margin={{ top: 24, right: 20, bottom: 24, left: 24 }}
                    >
                      <CartesianGrid strokeDasharray="2 3" stroke="var(--sol-ink-200)" vertical={false} />
                      <XAxis
                        dataKey="day"
                        axisLine={false}
                        tickLine={false}
                        tick={{
                          fontFamily: 'var(--sol-font-mono)',
                          fontSize: 11,
                          fill: 'var(--sol-ink-700)',
                        }}
                        interval={0}
                      />
                      <YAxis
                        axisLine={false}
                        tickLine={false}
                        tick={{
                          fontFamily: 'var(--sol-font-mono)',
                          fontSize: 10,
                          fill: 'var(--sol-ink-400)',
                        }}
                        width={52}
                        tickFormatter={(v) =>
                          v >= 1000
                            ? `${(v / 1000).toFixed(1).replace('.', ',')}k`
                            : String(Math.round(v))
                        }
                      />
                      <RechartsTooltip
                        contentStyle={{
                          background: 'var(--sol-bg-paper)',
                          border: '1px solid var(--sol-rule)',
                          borderRadius: 4,
                          fontFamily: 'var(--sol-font-mono)',
                          fontSize: 11,
                          color: 'var(--sol-ink-900)',
                        }}
                        formatter={(value) => [
                          value != null
                            ? `${Math.round(value).toLocaleString('fr-FR')} kWh`
                            : '—',
                          'consommation',
                        ]}
                      />
                      {weekAverage != null && (
                        <ReferenceLine
                          y={weekAverage}
                          stroke="var(--sol-calme-fg)"
                          strokeDasharray="4 3"
                          strokeWidth={1}
                          label={{
                            value: `moyenne`,
                            position: 'insideTopRight',
                            fill: 'var(--sol-calme-fg)',
                            fontFamily: 'var(--sol-font-mono)',
                            fontSize: 9,
                            fontWeight: 600,
                          }}
                        />
                      )}
                      <Bar dataKey="kwh" radius={[3, 3, 0, 0]} barSize={28}>
                        {weekChartData.map((entry, idx) => (
                          <Cell
                            key={entry.rawDate || idx}
                            fill={
                              entry.isMissing
                                ? 'var(--sol-ink-200)'
                                : idx === weekChartData.length - 1
                                  ? 'var(--sol-calme-fg)'
                                  : 'var(--sol-ink-700)'
                            }
                            fillOpacity={entry.isMissing ? 0.4 : 1}
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <div
                  style={{
                    display: 'flex',
                    gap: 16,
                    marginTop: 8,
                    fontSize: 10,
                    color: 'var(--sol-ink-500)',
                    fontFamily: 'var(--sol-font-mono)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.08em',
                  }}
                >
                  <span>
                    <span
                      style={{
                        display: 'inline-block',
                        width: 10,
                        height: 10,
                        background: 'var(--sol-ink-700)',
                        marginRight: 5,
                        verticalAlign: 'middle',
                        borderRadius: 2,
                      }}
                    />
                    jours précédents
                  </span>
                  <span>
                    <span
                      style={{
                        display: 'inline-block',
                        width: 10,
                        height: 10,
                        background: 'var(--sol-calme-fg)',
                        marginRight: 5,
                        verticalAlign: 'middle',
                        borderRadius: 2,
                      }}
                    />
                    hier
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Répartition HP/HC — composition tarifaire représentative de la semaine. */}
          {hpcShare && (
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <SolSectionHead
                title="Heures pleines / creuses · 7 derniers jours"
                meta={
                  loadCurveIsMock
                    ? 'Estimation profil bureau type · CDC non raccordée'
                    : `Calculé sur le profil J-1 (représentatif de la semaine)`
                }
              />
              <div
                style={{
                  background: 'var(--sol-bg-paper)',
                  border: '1px solid var(--sol-ink-200)',
                  borderRadius: 8,
                  padding: 20,
                  height: '100%',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  gap: 18,
                  minHeight: 240,
                }}
              >
                {/* Big numbers */}
                <div style={{ display: 'flex', gap: 20, alignItems: 'baseline' }}>
                  <div style={{ flex: 1 }}>
                    <div
                      style={{
                        fontSize: 10,
                        color: 'var(--sol-hph-fg, #b84545)',
                        textTransform: 'uppercase',
                        letterSpacing: '0.1em',
                        fontFamily: 'var(--sol-font-mono)',
                        marginBottom: 4,
                        fontWeight: 600,
                      }}
                    >
                      Heures pleines
                    </div>
                    <div
                      style={{
                        fontFamily: 'var(--sol-font-display)',
                        fontSize: 36,
                        color: 'var(--sol-hph-fg, #b84545)',
                        lineHeight: 1,
                      }}
                    >
                      {hpcShare.hpPct}
                      <span style={{ fontSize: 18, color: 'var(--sol-ink-500)' }}>%</span>
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--sol-ink-500)', marginTop: 4 }}>
                      06h–22h · plage tarifaire HP
                    </div>
                  </div>
                  <div style={{ flex: 1 }}>
                    <div
                      style={{
                        fontSize: 10,
                        color: 'var(--sol-hch-fg, #2e4a6b)',
                        textTransform: 'uppercase',
                        letterSpacing: '0.1em',
                        fontFamily: 'var(--sol-font-mono)',
                        marginBottom: 4,
                        fontWeight: 600,
                      }}
                    >
                      Heures creuses
                    </div>
                    <div
                      style={{
                        fontFamily: 'var(--sol-font-display)',
                        fontSize: 36,
                        color: 'var(--sol-hch-fg, #2e4a6b)',
                        lineHeight: 1,
                      }}
                    >
                      {hpcShare.hcPct}
                      <span style={{ fontSize: 18, color: 'var(--sol-ink-500)' }}>%</span>
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--sol-ink-500)', marginTop: 4 }}>
                      22h–06h · plage tarifaire HC
                    </div>
                  </div>
                </div>

                {/* Horizontal split bar */}
                <div
                  style={{
                    display: 'flex',
                    height: 12,
                    borderRadius: 6,
                    overflow: 'hidden',
                    boxShadow: 'inset 0 0 0 1px var(--sol-ink-200)',
                  }}
                  title={`HP ${hpcShare.hpPct}% · HC ${hpcShare.hcPct}%`}
                >
                  <div
                    style={{
                      width: `${hpcShare.hpPct}%`,
                      background: 'var(--sol-hph-bg, #fbe9e9)',
                      borderRight:
                        hpcShare.hpPct > 0 && hpcShare.hcPct > 0
                          ? '1px solid var(--sol-ink-200)'
                          : 'none',
                    }}
                  />
                  <div
                    style={{
                      width: `${hpcShare.hcPct}%`,
                      background: 'var(--sol-hch-bg, #e6edf5)',
                    }}
                  />
                </div>

                {/* Caption interprétation cost-optim sur la semaine. */}
                <div
                  style={{
                    fontSize: 12.5,
                    color: 'var(--sol-ink-500)',
                    lineHeight: 1.45,
                  }}
                >
                  {hpcShare.hpPct >= 80 ? (
                    <>
                      <strong style={{ color: 'var(--sol-ink-900)' }}>
                        Profil bureau type sur la semaine
                      </strong>{' '}
                      — contrat HP/HC bien calibré, peu de marge à activer.
                    </>
                  ) : hpcShare.hpPct >= 60 ? (
                    <>
                      <strong style={{ color: 'var(--sol-ink-900)' }}>
                        Profil mixte sur la semaine
                      </strong>{' '}
                      — examiner si une part de HP peut basculer en HC.
                    </>
                  ) : (
                    <>
                      <strong style={{ color: 'var(--sol-ink-900)' }}>
                        Forte part HC sur la semaine
                      </strong>{' '}
                      — opportunité de renégocier le contrat tarifaire.
                    </>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* 5. Profil horaire J-1 + seuil 80% — discipline HP/HC quotidienne.
          Toujours rendu : si seed n'a pas de CDC, on affiche le profil bureau type
          en aperçu (signature iconique conservée). */}
      <SolSectionHead
        title={loadCurveIsMock ? 'Profil horaire · aperçu 24 h' : 'Profil horaire J-1'}
        meta={
          loadCurveIsMock
            ? 'Données détaillées en cours de raccordement · profil bureau type'
            : `pas 15 min · HP/HC tarifaires${
                peakPoint ? ` · seuil 80% = ${Math.round(peakPoint.value * 0.8)} kW` : ''
              }`
        }
      />
      <div
        style={{
          background: 'var(--sol-bg-paper)',
          border: '1px solid var(--sol-ink-200)',
          borderRadius: 8,
          padding: 16,
        }}
      >
        <SolLoadCurve
          data={loadCurveData}
          peakPoint={peakPoint}
          peakThreshold={0.8}
          hpStart="06:00"
          hpEnd="22:00"
          caption={
            <>
              <strong style={{ color: 'var(--sol-ink-900)' }}>Seuil 80% du pic</strong> —
              ligne ambre pointillée. Au-dessus = discipline HP/HC à resserrer.
              {loadCurveIsMock && (
                <span style={{ color: 'var(--sol-ink-400)', marginLeft: 8 }}>
                  (aperçu estimé, courbe réelle en cours de raccordement Enedis)
                </span>
              )}
            </>
          }
          sourceChip={
            <SolSourceChip
              kind={loadCurveIsMock ? 'Estimé' : 'Enedis CDC'}
              origin={loadCurveIsMock ? 'profil bureau type' : 'profil 15 min'}
              freshness={loadCurveIsMock ? undefined : 'J-1'}
            />
          }
        />
      </div>

      {/* Watchlist déplacée dans le grid 2-col ci-dessus (pair avec TodayActions). */}

      {/* 5. Tuiles de navigation modules — accès cross-stream */}
      <SolSectionHead
        title="Accès rapide aux modules"
        meta={`${MODULE_TILES.length}${NBSP}modules`}
      />
      <div style={TILE_GRID_STYLE}>
        {MODULE_TILES.map(({ to, label, desc, Icon }) => (
          <button
            key={to}
            type="button"
            onClick={() => navigate(to)}
            style={TILE_STYLE}
            onMouseEnter={tileHoverEnter}
            onMouseLeave={tileHoverLeave}
          >
            <Icon size={20} style={TILE_ICON_STYLE} />
            <div style={TILE_BODY_STYLE}>
              <div style={TILE_LABEL_STYLE}>{label}</div>
              <div style={TILE_DESC_STYLE}>{desc}</div>
            </div>
          </button>
        ))}
      </div>
    </>
  );
}
