/**
 * AnomaliesPage — V114 Centre d'actions
 * Hub unique : onglet "Anomalies" (cross-sites) + onglet "Plan d'actions" (ActionsPage).
 * Route : /anomalies   — ?tab=actions pour le plan d'actions.
 */
import { useState, useEffect, useMemo, useRef, useCallback, lazy, Suspense } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  AlertTriangle,
  Search,
  X,
  Euro,
  ChevronRight,
  Building2,
  Upload,
  ArrowDownWideNarrow,
  HelpCircle,
  MoreHorizontal,
  Link2,
  Ban,
} from 'lucide-react';
import {
  PageShell,
  EmptyState,
  Tooltip,
  InfoTip,
  EvidenceDrawer,
  ActiveFiltersBar,
  Explain,
  KpiCardInline,
} from '../ui';
import Tabs from '../ui/Tabs';
import { useScope } from '../contexts/ScopeContext';
import { scopeKicker } from '../utils/format';
import SolPageHeader from '../ui/sol/SolPageHeader';
// Sprint 2 Vague B ét8' — HOC SolBriefingHead/Footer factorise grammaire §5.
import SolBriefingHead from '../ui/sol/SolBriefingHead';
import SolBriefingFooter from '../ui/sol/SolBriefingFooter';
import { usePageBriefing } from '../hooks/usePageBriefing';
import {
  getPatrimoineAnomalies,
  getBillingAnomaliesScoped,
  getAnomalyStatuses,
  dismissAnomaly,
} from '../services/api';
import { useActionDrawer } from '../contexts/ActionDrawerContext';
import { useToast } from '../ui/ToastProvider';
import useAnomalyFilters from './useAnomalyFilters';
import { buildAnomalyEvidence } from './anomalyEvidence';
import { fmtEur } from '../utils/format';

const ActionsPageInline = lazy(() => import('./ActionsPage'));

const CENTRE_TABS = [
  { id: 'anomalies', label: 'Anomalies' },
  { id: 'actions', label: "Plan d'actions" },
];

/* ── Constantes ── */

const MAX_SITES = 20;

const SEV_LABEL = { CRITICAL: 'Critique', HIGH: 'Élevé', MEDIUM: 'Moyen', LOW: 'Faible' };
// Sprint 1.9bis P0-5 (audit UI/Visual + Ergo) : palette migrée tokens warm
// Sol §6.2 « journal en terrasse » + contrastes WCAG AA. Inline style
// pour Tailwind v4 arbitrary-value bug (cf S1.5bis P0-4 leçon).
const SEV_STYLES = {
  CRITICAL: { background: 'var(--sol-refuse-bg)', color: 'var(--sol-refuse-fg)' },
  HIGH: { background: 'var(--sol-afaire-bg)', color: 'var(--sol-afaire-fg)' },
  MEDIUM: { background: 'var(--sol-attention-bg)', color: 'var(--sol-attention-fg)' },
  LOW: { background: 'var(--sol-ink-100)', color: 'var(--sol-ink-700)' },
};
const FW_LABEL = { DECRET_TERTIAIRE: 'Décret Tertiaire', FACTURATION: 'Facturation', BACS: 'BACS' };
// Frameworks → 1 chip neutre slate + couleur sévérité distincte (pattern Linear).
const FW_STYLES = {
  DECRET_TERTIAIRE: { background: 'var(--sol-bg-panel)', color: 'var(--sol-ink-700)' },
  FACTURATION: { background: 'var(--sol-bg-panel)', color: 'var(--sol-ink-700)' },
  BACS: { background: 'var(--sol-bg-panel)', color: 'var(--sol-ink-700)' },
};

/* fmtEur imported from ../utils/format */

/* ── Page ── */

export default function AnomaliesPage() {
  const navigate = useNavigate();
  const { filters, hasFilters, setFilters, resetFilters } = useAnomalyFilters();
  const activeTab = filters.tab;
  const { scopedSites, sitesLoading, org } = useScope();
  const { openActionDrawer } = useActionDrawer();

  // Sprint 1.9 — briefing éditorial Sol §5 vue Centre d'actions (ADR-001).
  // Page transverse §3 P11 : agrège anomalies cross-pillar (Conformité +
  // Performance + Facturation + Achat) via ActionItem (SoT unifiée).
  // Sert Marie DAF (priorisation hebdomadaire) + Investisseur (orchestration
  // produit unifié vs concurrents siloés).
  const {
    briefing: solBriefing,
    error: solBriefingError,
    refetch: solBriefingRefetch,
  } = usePageBriefing('anomalies', { persona: 'daily' });

  const { toast } = useToast();

  const [anomalies, setAnomalies] = useState([]); // flat [{...anomaly, site_id, site_nom}]
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const fetchIdRef = useRef(0);

  // V117: Anomaly statuses (linked/dismissed)
  const [anomalyStatuses, setAnomalyStatuses] = useState({}); // key: "source:ref:siteId" → status obj
  const [dismissMenuOpen, setDismissMenuOpen] = useState(null); // anomaly key or null

  // Evidence drawer
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const [evidenceData, setEvidenceData] = useState(null);

  // Sprint 1.9bis P0-1 : honorer deep-link `?action={id}` venant des
  // week-cards backend → ouvrir Evidence Drawer post-load.
  // Récurrence S1.6/1.7/1.8/1.9 corrigée via useSearchParams direct.
  const [searchParams] = useSearchParams();
  const queryActionId = searchParams.get('action');
  useEffect(() => {
    if (!queryActionId || anomalies.length === 0 || evidenceOpen) return;
    const target = anomalies.find(
      (a) =>
        String(a.code || a.id) === String(queryActionId) || String(a.id) === String(queryActionId)
    );
    if (target) {
      setEvidenceData(buildAnomalyEvidence(target));
      setEvidenceOpen(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [queryActionId, anomalies]);

  /* ── Fetch anomalies ── */
  useEffect(() => {
    if (scopedSites.length === 0) {
      setAnomalies([]);
      setLoading(false);
      return;
    }
    const sitesToFetch = scopedSites.slice(0, MAX_SITES);
    const fetchId = ++fetchIdRef.current;
    setLoading(true);
    setError(null);

    const patrimoinePromises = sitesToFetch.map((site) =>
      getPatrimoineAnomalies(site.id)
        .then((data) => ({ site, data, ok: true }))
        .catch(() => ({ site, data: null, ok: false }))
    );
    const billingPromise = getBillingAnomaliesScoped()
      .then((data) => ({ data, ok: true }))
      .catch(() => ({ data: null, ok: false }));

    Promise.all([...patrimoinePromises, billingPromise])
      .then((allResults) => {
        if (fetchIdRef.current !== fetchId) return;
        const billingResult = allResults[allResults.length - 1];
        const patrimoineResults = allResults.slice(0, -1);

        const flat = patrimoineResults.flatMap(({ site, data, ok }) => {
          if (!ok || !data) return [];
          return (data.anomalies ?? []).map((a) => ({
            ...a,
            site_id: site.id,
            site_nom: site.nom,
          }));
        });

        // Merge billing anomalies — normalize to patrimoine format
        // Filter by scopedSites so the scope bar selection is respected
        const scopedIds = new Set(sitesToFetch.map((s) => String(s.id)));
        if (billingResult.ok && billingResult.data?.anomalies?.length) {
          for (const b of billingResult.data.anomalies) {
            if (b.site_id && !scopedIds.has(String(b.site_id))) continue;
            flat.push({
              ...b,
              site_id: b.site_id ?? null,
              site_nom: b.site_nom || b.site_name || 'Facturation',
              regulatory_impact: { framework: 'FACTURATION' },
              _isBilling: true,
            });
          }
        }

        setAnomalies(flat);
        setLoading(false);
      })
      .catch(() => {
        if (fetchIdRef.current !== fetchId) return;
        setError('Impossible de charger les anomalies du parc.');
        setLoading(false);
      });
  }, [scopedSites]);

  /* ── Filtrage + tri ── */
  // Sprint 1.9bis P0-1 : filtre `status` honore deep-link week-cards backend
  // (?status=open|done). Mappe vers anomalyStatuses V117 (open/dismissed/done).
  const filtered = useMemo(() => {
    let r = [...anomalies];
    if (filters.fw) r = r.filter((a) => a.regulatory_impact?.framework === filters.fw);
    if (filters.sev) r = r.filter((a) => a.severity === filters.sev);
    if (filters.site) r = r.filter((a) => String(a.site_id) === filters.site);
    if (filters.status) {
      r = r.filter((a) => {
        const key = `${a._isBilling ? 'billing' : 'patrimoine'}:${a.code || a.id}:${a.site_id || ''}`;
        const st = anomalyStatuses[key];
        if (filters.status === 'open') return !st || st.status === 'open';
        if (filters.status === 'done' || filters.status === 'resolved') {
          return st?.status === 'resolved' || st?.status === 'done';
        }
        if (filters.status === 'dismissed' || filters.status === 'false_positive') {
          return st?.status === 'dismissed' || st?.status === 'false_positive';
        }
        return true;
      });
    }
    if (filters.q) {
      const q = filters.q.toLowerCase();
      r = r.filter(
        (a) => a.title_fr?.toLowerCase().includes(q) || a.site_nom?.toLowerCase().includes(q)
      );
    }
    // Tri : impact € DESC puis priority_score DESC
    r.sort((a, b) => {
      const ra = a.business_impact?.estimated_risk_eur ?? 0;
      const rb = b.business_impact?.estimated_risk_eur ?? 0;
      if (rb !== ra) return rb - ra;
      return (b.priority_score ?? 0) - (a.priority_score ?? 0);
    });
    return r;
  }, [
    anomalies,
    anomalyStatuses,
    filters.fw,
    filters.sev,
    filters.site,
    filters.status,
    filters.q,
  ]);

  /* ── KPIs (reflètent les filtres actifs) ── */
  const kpis = useMemo(() => {
    const total = filtered.length;
    const critiques = filtered.filter((a) => a.severity === 'CRITICAL').length;
    const risque = filtered.reduce((s, a) => s + (a.business_impact?.estimated_risk_eur ?? 0), 0);
    return { total, critiques, risque };
  }, [filtered]);

  /* ── V117: Fetch anomaly statuses when anomalies change ── */
  useEffect(() => {
    if (anomalies.length === 0) return;
    const batch = anomalies.map((a) => ({
      anomaly_source: a._isBilling ? 'billing' : 'patrimoine',
      anomaly_ref: a.code || a.id,
      site_id: a.site_id,
    }));
    getAnomalyStatuses(batch)
      .then((res) => {
        const map = {};
        for (const s of res.statuses || []) {
          const key = `${s.anomaly_source}:${s.anomaly_ref}:${s.site_id}`;
          map[key] = s;
        }
        setAnomalyStatuses(map);
      })
      .catch(() => {}); // non-bloquant
  }, [anomalies]);

  const getAnomalyKey = useCallback(
    (anom) =>
      `${anom._isBilling ? 'billing' : 'patrimoine'}:${anom.code || anom.id}:${anom.site_id}`,
    []
  );

  /* ── Helpers ── */
  function openTarget(anom) {
    if (anom._isBilling) {
      navigate('/bill-intel');
    } else if (anom.regulatory_impact?.framework === 'BACS') {
      navigate('/conformite', { state: { tab: 'bacs' } });
    } else if (anom.code?.startsWith('MISSING_') || anom.code?.startsWith('LOW_')) {
      navigate('/patrimoine', { state: { openSiteId: anom.site_id, openTab: 'donnees' } });
    } else {
      navigate('/patrimoine', { state: { openSiteId: anom.site_id, openTab: 'anomalies' } });
    }
  }

  function getOpenLabel(anom) {
    if (anom._isBilling) return 'Ouvrir facture';
    if (anom.regulatory_impact?.framework === 'BACS') return 'Ouvrir BACS';
    if (anom.code?.startsWith('MISSING_') || anom.code?.startsWith('LOW_'))
      return 'Corriger donnée';
    return 'Ouvrir fiche';
  }

  async function handleDismiss(anom, reasonCode) {
    try {
      await dismissAnomaly({
        anomaly_source: anom._isBilling ? 'billing' : 'patrimoine',
        anomaly_ref: anom.code || anom.id,
        site_id: anom.site_id,
        reason_code: reasonCode,
      });
      const key = getAnomalyKey(anom);
      setAnomalyStatuses((prev) => ({
        ...prev,
        [key]: { ...prev[key], status: 'dismissed' },
      }));
      setDismissMenuOpen(null);
      toast('Anomalie ignorée', 'success');
    } catch {
      toast("Erreur lors de l'ignorance", 'error');
    }
  }

  /* ── Rendu ── */
  // Sprint 1.9bis P0-3 (audit CX P0-1 + UX P0 + Espaces P0-2) : préambule
  // éditorial Sol §5 garanti dans toutes les branches dégradées (pattern
  // S1.7bis monitoringEditorialFallback). Évite flash legacy + rupture
  // grammaire + EmptyState plein écran sans contexte (§6.1).
  const anomaliesEditorialFallback = (
    <SolPageHeader
      kicker={scopeKicker("CENTRE D'ACTIONS", org?.nom, scopedSites?.length)}
      title="Vos anomalies, regroupées et priorisées"
      italicHook="4 piliers, 1 plan d'actions priorisé"
    />
  );

  if (sitesLoading) {
    return (
      <PageShell
        icon={AlertTriangle}
        title="Centre d'actions"
        editorialHeader={anomaliesEditorialFallback}
      >
        <div role="status" aria-live="polite" className="space-y-2 animate-pulse">
          <span className="sr-only">Chargement</span>
          {[...Array(4)].map((_, i) => (
            <div
              key={i}
              className="h-14 rounded-lg"
              style={{ background: 'var(--sol-bg-panel)' }}
            />
          ))}
        </div>
      </PageShell>
    );
  }

  if (scopedSites.length === 0) {
    return (
      <PageShell
        icon={AlertTriangle}
        title="Centre d'actions"
        editorialHeader={anomaliesEditorialFallback}
      >
        <EmptyState
          icon={Building2}
          title="Aucun site dans le scope"
          text={
            <>
              Importez votre <Explain term="patrimoine">patrimoine</Explain> ou chargez les données
              de démonstration pour voir les <Explain term="anomalie">anomalies</Explain>. Le centre
              d'actions centralise toutes les alertes et recommandations issues de l'analyse de vos
              données.
            </>
          }
          ctaLabel="Importer mon patrimoine"
          onCta={() => navigate('/import')}
          actions={
            <button
              onClick={() => navigate('/import')}
              className="flex items-center gap-1.5 text-sm font-semibold text-blue-600 bg-blue-50 border border-blue-100 rounded-lg px-4 py-2 hover:bg-blue-100 transition"
            >
              <Upload size={14} /> Charger la démo
            </button>
          }
        />
      </PageShell>
    );
  }

  const subtitle = loading ? (
    'Chargement des anomalies...'
  ) : (
    <>
      {kpis.total} <Explain term="anomalie">anomalie{kpis.total > 1 ? 's' : ''}</Explain> ·{' '}
      {kpis.critiques} critique{kpis.critiques > 1 ? 's' : ''} · {fmtEur(kpis.risque)} de risque
      estimé
    </>
  );

  return (
    <PageShell
      icon={AlertTriangle}
      title="Centre d'actions"
      editorialHeader={
        <SolPageHeader
          kicker={
            solBriefing?.kicker || scopeKicker("CENTRE D'ACTIONS", org?.nom, scopedSites?.length)
          }
          title={solBriefing?.title || 'Vos anomalies, regroupées et priorisées'}
          italicHook={solBriefing?.italicHook || 'conformité · performance · facturation · achat'}
          subtitle={activeTab === 'anomalies' ? subtitle : undefined}
        />
      }
    >
      {/* Sprint 2 Vague B ét8' — préambule §5 factorisé via SolBriefingHead. */}
      <SolBriefingHead
        briefing={solBriefing}
        error={solBriefingError}
        onRetry={solBriefingRefetch}
        omitHeader
        onNavigate={navigate}
      />

      <Tabs
        tabs={CENTRE_TABS}
        active={activeTab}
        onChange={(tab) => setFilters({ tab })}
        moduleKey="operations"
      />

      {activeTab === 'actions' ? (
        <Suspense
          fallback={
            <div className="space-y-2 animate-pulse mt-4">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-14 bg-gray-100 rounded-lg" />
              ))}
            </div>
          }
        >
          <ActionsPageInline bare />
        </Suspense>
      ) : (
        <div className="space-y-4">
          {/* Sprint 1.9bis P0-2 (audit UX/UI/Densité/Frontend-design) :
              KPI row supprimée — dupliquait les 3 KPIs hero SolNarrative
              (36px Stripe-grade) + cassait hiérarchie avec icônes blanches
              sur bg-blue-600/red-600/amber-600 saturés. SoT unique
              above-the-fold = SolNarrative.kpis. */}

          {/* ── Toolbar ── */}
          <div className="flex items-center gap-2 flex-wrap">
            {/* Recherche texte */}
            <div className="relative flex-1 min-w-[180px] max-w-sm">
              <Search
                size={14}
                className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400"
              />
              <input
                type="text"
                placeholder="Rechercher une anomalie ou un site..."
                value={filters.q}
                onChange={(e) => setFilters({ q: e.target.value })}
                className="w-full pl-8 pr-3 py-1.5 border border-gray-200 rounded-lg text-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
              />
            </div>

            {/* Framework */}
            <QuickSelect
              value={filters.fw}
              onChange={(v) => setFilters({ fw: v })}
              options={[
                { value: '', label: 'Framework' },
                { value: 'DECRET_TERTIAIRE', label: 'Décret Tertiaire' },
                { value: 'FACTURATION', label: 'Facturation' },
                { value: 'BACS', label: 'BACS' },
              ]}
            />

            {/* Sévérité */}
            <QuickSelect
              value={filters.sev}
              onChange={(v) => setFilters({ sev: v })}
              options={[
                { value: '', label: 'Sévérité' },
                { value: 'CRITICAL', label: 'Critique' },
                { value: 'HIGH', label: 'Élevé' },
                { value: 'MEDIUM', label: 'Moyen' },
                { value: 'LOW', label: 'Faible' },
              ]}
            />

            {/* Site */}
            <QuickSelect
              value={filters.site}
              onChange={(v) => setFilters({ site: v })}
              options={[
                { value: '', label: 'Tous les sites' },
                ...scopedSites
                  .slice(0, MAX_SITES)
                  .map((s) => ({ value: String(s.id), label: s.nom })),
              ]}
            />

            {/* Reset */}
            {hasFilters && (
              <button
                onClick={resetFilters}
                className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 transition"
              >
                <X size={12} /> Réinitialiser
              </button>
            )}

            {/* Smart sort indicator */}
            <span className="ml-auto flex items-center gap-1 text-[11px] text-gray-400 font-medium select-none">
              <ArrowDownWideNarrow size={12} />
              Tri intelligent actif
              <InfoTip
                content="Les anomalies sont triées par impact financier (risque EUR) décroissant, puis par score de priorité. Le score combine la sévérité, le risque réglementaire et l'impact métier."
                position="bottom"
              />
            </span>
          </div>

          {/* ── Active filters bar ── */}
          <ActiveFiltersBar
            filters={[
              filters.fw && {
                key: 'fw',
                label: 'Framework',
                value: FW_LABEL[filters.fw] ?? filters.fw,
                onRemove: () => setFilters({ fw: '' }),
              },
              filters.sev && {
                key: 'sev',
                label: 'Sévérité',
                value: SEV_LABEL[filters.sev] ?? filters.sev,
                onRemove: () => setFilters({ sev: '' }),
              },
              filters.site && {
                key: 'site',
                label: 'Site',
                value: scopedSites.find((s) => String(s.id) === filters.site)?.nom ?? filters.site,
                onRemove: () => setFilters({ site: '' }),
              },
              filters.q && {
                key: 'q',
                label: 'Recherche',
                value: filters.q,
                onRemove: () => setFilters({ q: '' }),
              },
            ].filter(Boolean)}
            total={anomalies.length}
            filtered={filtered.length}
            onReset={resetFilters}
          />

          {/* ── Erreur ── */}
          {error && (
            <div className="flex items-center gap-2 text-xs text-red-600 bg-red-50 border border-red-100 rounded-lg px-4 py-2">
              <AlertTriangle size={13} className="shrink-0" /> {error}
            </div>
          )}

          {/* ── Liste anomalies ── */}
          {loading ? (
            <div className="space-y-2 animate-pulse">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-14 bg-gray-100 rounded-lg" />
              ))}
            </div>
          ) : filtered.length === 0 ? (
            <div className="text-center py-10 text-gray-400">
              <Search size={28} className="mx-auto mb-2" />
              <p className="text-sm font-medium text-gray-600">
                Aucune <Explain term="anomalie">anomalie</Explain> ne correspond
              </p>
              {hasFilters && (
                <button
                  onClick={resetFilters}
                  className="mt-2 text-xs text-blue-600 hover:underline"
                >
                  Réinitialiser les filtres
                </button>
              )}
            </div>
          ) : (
            <div className="space-y-1.5">
              {filtered.map((anom, idx) => {
                const impactFmt = fmtEur(anom.business_impact?.estimated_risk_eur);

                return (
                  <div
                    key={`${anom.site_id}-${anom.code}-${idx}`}
                    className="flex items-start gap-3 px-3 py-2.5 bg-white border border-gray-100 rounded-lg hover:border-gray-200 transition"
                  >
                    {/* Infos anomalie */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        {/* Site */}
                        <span className="text-[10px] font-medium text-gray-500 bg-gray-100 rounded px-1.5 py-0.5 shrink-0">
                          {anom.site_nom}
                        </span>
                        {/* Severity — Sprint 1.9bis tokens warm Sol §6.2 */}
                        <span
                          className="text-[10px] font-semibold px-1.5 py-0.5 rounded shrink-0"
                          style={
                            SEV_STYLES[anom.severity] || {
                              background: 'var(--sol-ink-100)',
                              color: 'var(--sol-ink-700)',
                            }
                          }
                        >
                          {SEV_LABEL[anom.severity] ?? anom.severity}
                        </span>
                        {/* Framework — Sprint 1.9bis chip neutre slate (pattern Linear) */}
                        {anom.regulatory_impact?.framework &&
                          anom.regulatory_impact.framework !== 'NONE' && (
                            <span
                              className="text-[9px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded shrink-0"
                              style={
                                FW_STYLES[anom.regulatory_impact.framework] || {
                                  background: 'var(--sol-ink-100)',
                                  color: 'var(--sol-ink-700)',
                                }
                              }
                            >
                              {FW_LABEL[anom.regulatory_impact.framework] ??
                                anom.regulatory_impact.framework}
                            </span>
                          )}
                        {/* Titre */}
                        <span className="text-sm font-medium text-gray-800 truncate">
                          {anom.title_fr}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                        {impactFmt !== '—' && (
                          <span className="text-[10px] text-gray-500 flex items-center gap-0.5">
                            <Euro size={9} /> {impactFmt}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* CTAs */}
                    {(() => {
                      const key = getAnomalyKey(anom);
                      const st = anomalyStatuses[key];
                      const isDismissed = st?.status === 'dismissed';
                      const isLinked = st?.status === 'linked' || st?.status === 'resolved';
                      const linkedCount = st?.linked_actions?.length || 0;

                      return (
                        <div className="flex items-center gap-1 shrink-0">
                          {/* Status badge */}
                          {isDismissed && (
                            <span className="text-[10px] font-medium text-gray-400 bg-gray-50 border border-gray-200 rounded px-1.5 py-0.5">
                              <Ban size={9} className="inline mr-0.5" />
                              Ignorée
                            </span>
                          )}
                          {isLinked && (
                            <button
                              type="button"
                              onClick={() => navigate(`/anomalies?tab=actions`)}
                              className="flex items-center gap-0.5 text-[10px] font-medium text-emerald-600 bg-emerald-50 border border-emerald-200 rounded px-1.5 py-0.5 hover:bg-emerald-100 transition"
                            >
                              <Link2 size={9} /> Voir action
                              {linkedCount > 1 ? `s (${linkedCount})` : ''}
                            </button>
                          )}

                          {/* Context-aware open button */}
                          {!isDismissed && (
                            <Tooltip text={`Ouvrir : ${getOpenLabel(anom)}`}>
                              <button
                                type="button"
                                onClick={() => openTarget(anom)}
                                className="flex items-center gap-1 text-[11px] font-medium text-blue-600 bg-blue-50 border border-blue-100 rounded px-2 py-1 hover:bg-blue-100 transition"
                              >
                                {getOpenLabel(anom)} <ChevronRight size={11} />
                              </button>
                            </Tooltip>
                          )}

                          {/* Create / link action */}
                          {!isDismissed && (
                            <Tooltip
                              text={
                                isLinked
                                  ? 'Créer une autre action'
                                  : 'Créer une action pour cette anomalie'
                              }
                            >
                              <button
                                type="button"
                                data-testid="creer-action-btn"
                                onClick={() =>
                                  openActionDrawer({
                                    prefill: { titre: anom.title_fr, type: 'anomalie' },
                                    siteId: anom.site_id,
                                    sourceType: 'anomaly',
                                    sourceId: anom.code,
                                    idempotencyKey: `anomaly:${anom.site_id}:${anom.code}`,
                                  })
                                }
                                className="text-[11px] font-medium text-gray-600 bg-gray-100 border border-gray-200 rounded px-2 py-1 hover:bg-gray-200 transition"
                              >
                                {isLinked ? '+ Action' : 'Créer une action'}
                              </button>
                            </Tooltip>
                          )}

                          {/* Pourquoi */}
                          <Tooltip text="Comprendre cette anomalie">
                            <button
                              type="button"
                              data-testid="pourquoi-btn"
                              onClick={() => {
                                setEvidenceData(buildAnomalyEvidence(anom));
                                setEvidenceOpen(true);
                              }}
                              className="flex items-center gap-0.5 text-[11px] font-medium text-purple-600 bg-purple-50 border border-purple-100 rounded px-2 py-1 hover:bg-purple-100 transition"
                            >
                              <HelpCircle size={11} /> Pourquoi ?
                            </button>
                          </Tooltip>

                          {/* Overflow menu: Ignorer */}
                          {!isDismissed && (
                            <div className="relative">
                              <button
                                type="button"
                                onClick={() =>
                                  setDismissMenuOpen(dismissMenuOpen === key ? null : key)
                                }
                                className="p-1 text-gray-400 hover:text-gray-600 rounded transition"
                                aria-label="Plus d'options"
                              >
                                <MoreHorizontal size={14} />
                              </button>
                              {dismissMenuOpen === key && (
                                <div className="absolute right-0 top-8 z-50 bg-white border border-gray-200 rounded-lg shadow-lg py-1 w-48">
                                  <p className="px-3 py-1 text-[10px] font-semibold text-gray-400 uppercase">
                                    Ignorer (motif requis)
                                  </p>
                                  {[
                                    { code: 'false_positive', label: 'Faux positif' },
                                    { code: 'known_issue', label: 'Problème connu' },
                                    { code: 'out_of_scope', label: 'Hors périmètre' },
                                    { code: 'duplicate', label: 'Doublon' },
                                  ].map((reason) => (
                                    <button
                                      key={reason.code}
                                      type="button"
                                      onClick={() => handleDismiss(anom, reason.code)}
                                      className="w-full text-left px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-50 transition"
                                    >
                                      {reason.label}
                                    </button>
                                  ))}
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })()}
                  </div>
                );
              })}

              <p className="text-[11px] text-gray-400 text-center pt-1">
                {filtered.length} résultat{filtered.length > 1 ? 's' : ''}
                {scopedSites.length > MAX_SITES &&
                  ` · ${MAX_SITES} sites analysés sur ${scopedSites.length}`}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Action Drawer — managed by ActionDrawerContext */}
      <EvidenceDrawer
        open={evidenceOpen}
        onClose={() => setEvidenceOpen(false)}
        evidence={evidenceData}
      />

      {/* Sprint 1.9 — SolPageFooter §5 (ADR-001).
          Source · Confiance · Mis à jour. Methodology URL pointe vers
          /methodologie/centre-actions (orchestration cross-pillar). */}
      {/* Sprint 2 Vague B ét8' — SolPageFooter §5 factorisé via HOC. */}
      <SolBriefingFooter briefing={solBriefing} />
    </PageShell>
  );
}

/* ── Sous-composants ── */

// KpiCard replaced by shared KpiCardInline from ui

function QuickSelect({ value, onChange, options }) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={`text-xs px-2.5 py-1.5 rounded-lg border bg-white cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500 ${
        value ? 'border-blue-300 text-blue-700 font-medium' : 'border-gray-200 text-gray-600'
      }`}
    >
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  );
}
