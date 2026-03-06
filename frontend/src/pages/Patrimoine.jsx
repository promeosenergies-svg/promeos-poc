/**
 * PROMEOS - Patrimoine V5 — Premium Command-Center Cockpit
 * Risk-first table · URL-synced filters · tabbed SiteDrawer · k€/m² formatting.
 */
import { useState, useMemo, useCallback, useEffect, useRef } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { useNavigate, useSearchParams, useLocation } from 'react-router-dom';
import {
  Building2,
  Search,
  Download,
  Star,
  Plus,
  Upload,
  MapPin,
  ChevronRight,
  ShieldCheck,
  AlertTriangle,
  BadgeEuro,
  Zap,
  ExternalLink,
  Eye,
  Lightbulb,
  X,
  ArrowUpDown,
} from 'lucide-react';
import {
  Card,
  Badge,
  Button,
  EmptyState,
  PageShell,
  KpiCardCompact,
  Drawer,
  Tabs,
  Tooltip,
} from '../ui';
import { Table, Thead, Tbody, Th, Tr, Td, ThCheckbox, TdCheckbox } from '../ui';
import { SkeletonCard, SkeletonTable } from '../ui/Skeleton';
import ErrorState from '../ui/ErrorState';
import { useScope } from '../contexts/ScopeContext';
import { useExpertMode } from '../contexts/ExpertModeContext';
import { useActionDrawer } from '../contexts/ActionDrawerContext';
import PatrimoineWizard from '../components/PatrimoineWizard';
import PatrimoinePortfolioHealthBar from '../components/PatrimoinePortfolioHealthBar';
import PatrimoineHeatmap from '../components/PatrimoineHeatmap';
import PatrimoineRiskDistributionBar from '../components/PatrimoineRiskDistributionBar';
import SiteAnomalyPanel from '../components/SiteAnomalyPanel';
import SegmentationWidget from '../components/SegmentationWidget';
import SegmentationQuestionnaireModal from '../components/SegmentationQuestionnaireModal';
import { getPatrimoineAnomalies, getPortfolioReconciliation } from '../services/api';
import { track } from '../services/tracker';
import {
  fmtEur,
  fmtEurFull,
  fmtArea,
  fmtAreaCompact,
  fmtKwh,
  fmtDateFR,
  pl,
} from '../utils/format';
import { RISK_THRESHOLDS, ANOMALY_THRESHOLDS, getStatusBadgeProps, getDataQualityGrade } from '../lib/constants';
import DataQualityBadge from '../components/DataQualityBadge';
import { getDataQualityPortfolio } from '../services/api';

/* ─── Constants ──────────────────────────────────────────── */

const ROW_HEIGHT = 52; // px — fixed row height for virtual scroll
const OVERSCAN = 10; // extra rows above/below viewport

const USAGE_OPTIONS = [
  { value: '', label: 'Usage' },
  { value: 'bureau', label: 'Bureau' },
  { value: 'commerce', label: 'Commerce' },
  { value: 'entrepot', label: 'Entrepot' },
  { value: 'hotel', label: 'Hotel' },
  { value: 'sante', label: 'Sante' },
  { value: 'enseignement', label: 'Enseignement' },
  { value: 'copropriete', label: 'Copropriete' },
  { value: 'collectivite', label: 'Collectivite' },
];

const STATUT_OPTIONS = [
  { value: '', label: 'Statut' },
  { value: 'conforme', label: 'Conforme' },
  { value: 'non_conforme', label: 'Non conforme' },
  { value: 'a_risque', label: 'À risque' },
  { value: 'a_evaluer', label: 'À évaluer' },
];

// Built from centralized STATUS_CONFIG — single source of truth
const _sb = (k) => {
  const { variant, label } = getStatusBadgeProps(k);
  return { status: variant, label };
};
const STATUT_BADGE = {
  conforme: _sb('conforme'),
  non_conforme: _sb('non_conforme'),
  a_risque: _sb('a_risque'),
  a_evaluer: _sb('a_evaluer'),
};

const USAGE_COLOR = {
  bureau: 'bg-blue-50 text-blue-700 ring-blue-200',
  commerce: 'bg-purple-50 text-purple-700 ring-purple-200',
  entrepot: 'bg-gray-100 text-gray-700 ring-gray-200',
  hotel: 'bg-amber-50 text-amber-700 ring-amber-200',
  sante: 'bg-red-50 text-red-700 ring-red-200',
  enseignement: 'bg-green-50 text-green-700 ring-green-200',
  copropriete: 'bg-indigo-50 text-indigo-700 ring-indigo-200',
  collectivite: 'bg-teal-50 text-teal-700 ring-teal-200',
};

const PRESET_VIEWS = [
  { id: 'risk', label: 'Risque (Top)', sort: 'risque_eur', dir: 'desc', filter: {} },
  {
    id: 'nc',
    label: 'Non conformes',
    sort: 'risque_eur',
    dir: 'desc',
    filter: { statut: 'non_conforme' },
  },
  { id: 'eval', label: 'À évaluer', sort: 'nom', dir: 'asc', filter: { statut: 'a_evaluer' } },
];

/* ─── Main Component ─────────────────────────────────────── */

export default function Patrimoine() {
  const navigate = useNavigate();
  const location = useLocation();
  const [sp, setSp] = useSearchParams();
  const { scopedSites, sitesLoading, scope } = useScope();
  const { isExpert } = useExpertMode();
  const searchRef = useRef(null);

  // URL-synced state
  const search = sp.get('q') || '';
  const filterUsage = sp.get('usage') || '';
  const filterStatut = sp.get('statut') || '';
  const filterAnomalies = sp.get('anomalies') === '1';
  const sortCol = sp.get('sort') || 'risque_eur';
  const sortDir = sp.get('dir') || 'desc';
  const activeView = sp.get('view') || '';

  const scrollRef = useRef(null);
  const [selected, setSelected] = useState(new Set());
  const { openActionDrawer } = useActionDrawer();
  const [showWizard, setShowWizard] = useState(false);
  const [showSegModal, setShowSegModal] = useState(false);
  const [drawerSite, setDrawerSite] = useState(null);
  const [drawerInitialTab, setDrawerInitialTab] = useState('resume');

  // V63 — Heatmap enrichie (anomalies par site, Promise.all, guard stale)
  const [hmTiles, setHmTiles] = useState([]);
  const [hmLoading, setHmLoading] = useState(false);
  const [hmError, setHmError] = useState(null);
  const hmFetchIdRef = useRef(0);

  const [favorites, setFavorites] = useState(() => {
    try {
      return new Set(JSON.parse(localStorage.getItem('promeos_fav_sites') || '[]'));
    } catch {
      return new Set();
    }
  });

  // V96 — Reconciliation badge per site
  const [reconMap, setReconMap] = useState({});
  useEffect(() => {
    getPortfolioReconciliation()
      .then((data) => {
        const m = {};
        (data.sites || []).forEach((s) => {
          m[s.site_id] = s;
        });
        setReconMap(m);
      })
      .catch(() => {});
  }, []);

  // D.1 — Data quality scores per site
  const [dqMap, setDqMap] = useState({});
  useEffect(() => {
    if (!org?.id) return;
    getDataQualityPortfolio(org.id)
      .then((data) => {
        const m = {};
        (data.sites || []).forEach((s) => { m[s.site_id] = s; });
        setDqMap(m);
      })
      .catch(() => {});
  }, [org?.id]);

  // URL param helper — merges params, removes empty values
  const setParams = useCallback(
    (patch) => {
      setSp(
        (prev) => {
          const next = new URLSearchParams(prev);
          Object.entries(patch).forEach(([k, v]) => {
            if (v === '' || v === null || v === false || v === undefined) next.delete(k);
            else next.set(k, String(v));
          });
          return next;
        },
        { replace: true }
      );
      scrollRef.current?.scrollTo({ top: 0 });
    },
    [setSp]
  );

  // Keyboard shortcut: "/" to focus search
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === '/' && !['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) {
        e.preventDefault();
        searchRef.current?.focus();
      }
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, []);

  // V65 — Auto-ouvrir drawer depuis AnomaliesPage (location.state)
  useEffect(() => {
    if (!location.state?.openSiteId) return;
    const site = scopedSites.find((s) => s.id === location.state.openSiteId);
    if (site) {
      setDrawerSite(site);
      setDrawerInitialTab(location.state.openTab || 'anomalies');
      navigate('.', { replace: true, state: {} }); // clear state
    }
  }, [location.state, scopedSites]); // eslint-disable-line react-hooks/exhaustive-deps

  // V63 — Enrichissement heatmap : anomalies par site (Promise.all, max 10 sites, guard stale)
  useEffect(() => {
    if (scopedSites.length === 0) {
      setHmTiles([]);
      setHmLoading(false);
      setHmError(null);
      return;
    }
    const sitesToFetch = scopedSites.slice(0, 10);
    setHmLoading(true);
    setHmError(null);

    const fetchId = ++hmFetchIdRef.current;

    const SEV_ORDER_MAP = { CRITICAL: 4, HIGH: 3, MEDIUM: 2, LOW: 1 };

    Promise.all(
      sitesToFetch.map((site) =>
        getPatrimoineAnomalies(site.id)
          .then((data) => ({ site, data, ok: true }))
          .catch(() => ({ site, data: null, ok: false }))
      )
    )
      .then((results) => {
        if (hmFetchIdRef.current !== fetchId) return; // réponse périmée
        const tiles = results.map(({ site, data, ok }) => {
          const anomalies = ok && data ? (data.anomalies ?? []) : [];

          // Mode framework dominant
          const fwCounts = {};
          for (const a of anomalies) {
            const fw = a.regulatory_impact?.framework ?? 'NONE';
            if (fw !== 'NONE') fwCounts[fw] = (fwCounts[fw] ?? 0) + 1;
          }
          const dominant_framework =
            Object.keys(fwCounts).length > 0
              ? Object.entries(fwCounts).sort((a, b) => b[1] - a[1])[0][0]
              : null;

          // Sévérité max
          const max_severity = anomalies.reduce((mx, a) => {
            const o = SEV_ORDER_MAP[a.severity] ?? 0;
            const mxo = SEV_ORDER_MAP[mx] ?? 0;
            return o > mxo ? a.severity : mx;
          }, null);

          return {
            site_id: site.id,
            site_nom: site.nom,
            total_risk_eur: ok && data ? data.total_estimated_risk_eur : (site.risque_eur ?? 0),
            anomalies_count: ok && data ? data.nb_anomalies : (site.anomalies_count ?? 0),
            max_severity,
            dominant_framework,
            completude_score: ok && data ? data.completude_score : 0,
            top_anomalies: anomalies.slice(0, 2).map((a) => ({
              code: a.code,
              severity: a.severity,
              title_fr: a.title_fr,
            })),
          };
        });
        setHmTiles(tiles);
        setHmLoading(false);
      })
      .catch(() => {
        if (hmFetchIdRef.current !== fetchId) return;
        setHmError('Impossible de charger la heatmap.');
        setHmLoading(false);
      });
  }, [scopedSites]);

  /* ─── Computed data ─── */

  const stats = useMemo(() => {
    const t = scopedSites.length;
    const conformes = scopedSites.filter((s) => s.statut_conformite === 'conforme').length;
    const nc = scopedSites.filter((s) => s.statut_conformite === 'non_conforme').length;
    const aRisque = scopedSites.filter((s) => s.statut_conformite === 'a_risque').length;
    const risque = scopedSites.reduce((a, s) => a + (s.risque_eur || 0), 0);
    const surface = scopedSites.reduce((a, s) => a + (s.surface_m2 || 0), 0);
    const anomalies = scopedSites.reduce((a, s) => a + (s.anomalies_count || 0), 0);
    const withAno = scopedSites.filter((s) => (s.anomalies_count || 0) > 0).length;
    return { total: t, conformes, nc, aRisque, risque, surface, anomalies, withAno };
  }, [scopedSites]);

  const filtered = useMemo(() => {
    let r = [...scopedSites];
    if (search) {
      const q = search.toLowerCase();
      r = r.filter(
        (s) =>
          s.nom.toLowerCase().includes(q) ||
          s.ville.toLowerCase().includes(q) ||
          (s.adresse || '').toLowerCase().includes(q) ||
          (s.code_postal || '').includes(q)
      );
    }
    if (filterUsage) r = r.filter((s) => s.usage === filterUsage);
    if (filterStatut) r = r.filter((s) => s.statut_conformite === filterStatut);
    if (filterAnomalies) r = r.filter((s) => (s.anomalies_count || 0) > 0);
    if (sortCol) {
      r.sort((a, b) => {
        const va = a[sortCol] ?? 0,
          vb = b[sortCol] ?? 0;
        if (typeof va === 'number') return sortDir === 'asc' ? va - vb : vb - va;
        return sortDir === 'asc'
          ? String(va).localeCompare(String(vb))
          : String(vb).localeCompare(String(va));
      });
    }
    return r;
  }, [scopedSites, search, filterUsage, filterStatut, filterAnomalies, sortCol, sortDir]);

  const total = filtered.length;

  // Virtual scroll
  const virtualizer = useVirtualizer({
    count: total,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: OVERSCAN,
  });

  const virtualItems = virtualizer.getVirtualItems();
  const paddingTop = virtualItems.length > 0 ? virtualItems[0].start : 0;
  const paddingBottom =
    virtualItems.length > 0
      ? virtualizer.getTotalSize() - virtualItems[virtualItems.length - 1].end
      : 0;
  const colCount = isExpert ? 12 : 11;

  const selectedStats = useMemo(() => {
    if (selected.size === 0) return null;
    const sites = scopedSites.filter((s) => selected.has(s.id));
    return { count: sites.length, risque: sites.reduce((a, s) => a + (s.risque_eur || 0), 0) };
  }, [selected, scopedSites]);

  /* ─── Handlers ─── */

  function handleSort(col) {
    if (sortCol === col) {
      const nd = sortDir === 'asc' ? 'desc' : sortDir === 'desc' ? '' : 'asc';
      setParams({ sort: nd ? col : '', dir: nd, view: '' });
      if (!nd) setParams({ sort: '', dir: '' });
    } else {
      setParams({ sort: col, dir: 'asc', view: '' });
    }
    track('filter_apply', { action: 'sort', col });
  }

  function resetFilters() {
    setSp({}, { replace: true });
    scrollRef.current?.scrollTo({ top: 0 });
    track('filter_apply', { action: 'reset' });
  }

  function applyPreset(view) {
    const p = { view: view.id, sort: view.sort, dir: view.dir, q: '', usage: '', anomalies: '' };
    if (view.filter.statut) p.statut = view.filter.statut;
    else p.statut = '';
    setSp(p, { replace: true });
    scrollRef.current?.scrollTo({ top: 0 });
    track('filter_apply', { action: 'preset', name: view.id });
  }

  function toggleSelect(id) {
    setSelected((prev) => {
      const n = new Set(prev);
      n.has(id) ? n.delete(id) : n.add(id);
      return n;
    });
  }
  function toggleSelectAll() {
    setSelected(selected.size === filtered.length ? new Set() : new Set(filtered.map((s) => s.id)));
  }

  function exportCsv() {
    const params = new URLSearchParams();
    if (filterUsage) params.set('type_site', filterUsage);
    if (search) params.set('search', search);
    window.open(`/api/patrimoine/sites/export.csv?${params.toString()}`, '_blank');
    track('export_csv', { server_side: true });
  }

  function toggleFavorites() {
    const n = new Set(favorites);
    for (const id of selected) {
      n.has(id) ? n.delete(id) : n.add(id);
    }
    setFavorites(n);
    localStorage.setItem('promeos_fav_sites', JSON.stringify([...n]));
    setSelected(new Set());
  }

  const openDrawer = useCallback((site) => {
    setDrawerSite(site);
    setDrawerInitialTab('resume');
    track('row_click', { site_id: site.id });
  }, []);

  // V60 — ouvre le drawer sur l'onglet Anomalies (depuis PatrimoinePortfolioHealthBar)
  const openDrawerOnAnomalies = useCallback(
    (site_id) => {
      const site = scopedSites.find((s) => s.id === site_id);
      if (site) {
        setDrawerSite(site);
        setDrawerInitialTab('anomalies');
        track('portfolio_top_site_click', { site_id });
      } else {
        navigate(`/sites/${site_id}`);
      }
    },
    [scopedSites, navigate]
  );
  const openActionFromDrawer = useCallback(
    (siteName, siteId) => {
      setDrawerSite(null);
      openActionDrawer({
        prefill: { site: siteName },
        siteId: siteId || null,
        sourceType: 'patrimoine',
      });
    },
    [openActionDrawer]
  );

  const _hasFilters = search || filterUsage || filterStatut || filterAnomalies;
  const activeChips = [];
  if (search) activeChips.push({ label: `"${search}"`, clear: () => setParams({ q: '' }) });
  if (filterUsage)
    activeChips.push({
      label: USAGE_OPTIONS.find((o) => o.value === filterUsage)?.label || filterUsage,
      clear: () => setParams({ usage: '' }),
    });
  if (filterStatut)
    activeChips.push({
      label: STATUT_OPTIONS.find((o) => o.value === filterStatut)?.label || filterStatut,
      clear: () => setParams({ statut: '' }),
    });
  if (filterAnomalies)
    activeChips.push({ label: 'Avec anomalies', clear: () => setParams({ anomalies: '' }) });

  /* ─── Render ─── */

  // Etat chargement
  if (sitesLoading) {
    return (
      <PageShell icon={Building2} title="Patrimoine" subtitle="Chargement...">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
        <SkeletonTable rows={8} cols={6} />
      </PageShell>
    );
  }

  const isEmptyPatrimoine = scopedSites.length === 0;

  // Dynamic subtitle
  const subtitle = isEmptyPatrimoine
    ? 'Importez votre patrimoine pour commencer'
    : `${pl(stats.total, 'site')} · ${fmtAreaCompact(stats.surface)} · ${stats.conformes} conformes · ${fmtEur(stats.risque)} de risque`;

  return (
    <PageShell
      icon={Building2}
      title="Patrimoine"
      subtitle={subtitle}
      actions={
        <>
          {!isEmptyPatrimoine && (
            <Button
              variant="secondary"
              size="sm"
              onClick={() => openActionDrawer({ sourceType: 'patrimoine' })}
            >
              <Plus size={14} className="mr-1" />
              Action
            </Button>
          )}
          <Button size="sm" onClick={() => setShowWizard(true)}>
            <Upload size={14} className="mr-1" />
            Importer
          </Button>
        </>
      }
    >
      {/* ── Welcome empty state ── */}
      {isEmptyPatrimoine ? (
        <EmptyState
          icon={Building2}
          title="Bienvenue sur PROMEOS"
          text="Importez votre patrimoine immobilier pour commencer le pilotage énergétique. CSV, Excel ou données de démonstration."
          ctaLabel="Importer mon patrimoine"
          onCta={() => setShowWizard(true)}
          actions={
            <Button variant="secondary" size="lg" onClick={() => setShowWizard(true)}>
              <Zap size={16} className="mr-2" />
              Demo
            </Button>
          }
        />
      ) : (
        <div className="space-y-3">
          {/* ── Portfolio Health Bar V60 — risque global, top sites, framework ── */}
          <PatrimoinePortfolioHealthBar onSiteClick={openDrawerOnAnomalies} orgId={scope.orgId} />

          {/* ── V63 — Heatmap portefeuille (risque / anomalies / framework par site) ── */}
          {/* ── V64 — Distribution du risque insérée via topSlot ── */}
          <PatrimoineHeatmap
            tiles={hmTiles}
            onOpenSite={openDrawerOnAnomalies}
            loading={hmLoading}
            error={hmError}
            topSlot={<PatrimoineRiskDistributionBar sites={filtered} />}
          />

          {/* ── KPI row (compact) ── */}
          <div className="grid grid-cols-4 gap-3">
            <KpiCardCompact
              icon={Building2}
              color="bg-blue-600"
              label="Sites actifs"
              value={stats.total}
              detail={fmtAreaCompact(stats.surface)}
              active={!filterStatut && !filterAnomalies && !activeView}
              onClick={() => setParams({ statut: '', anomalies: '', view: '' })}
            />
            <KpiCardCompact
              icon={ShieldCheck}
              color="bg-emerald-600"
              label="Conformes"
              value={stats.conformes}
              detail={
                stats.total > 0
                  ? `${Math.round((stats.conformes / stats.total) * 100)}% du parc`
                  : '—'
              }
              active={filterStatut === 'conforme'}
              onClick={() =>
                setParams({
                  statut: filterStatut === 'conforme' ? '' : 'conforme',
                  anomalies: '',
                  view: '',
                })
              }
            />
            <KpiCardCompact
              icon={AlertTriangle}
              color="bg-red-600"
              label="Non conformes"
              value={stats.nc + stats.aRisque}
              detail={`${stats.nc} NC · ${stats.aRisque} à risque`}
              active={filterStatut === 'non_conforme'}
              onClick={() =>
                setParams({
                  statut: filterStatut === 'non_conforme' ? '' : 'non_conforme',
                  anomalies: '',
                  view: '',
                })
              }
            />
            <KpiCardCompact
              icon={BadgeEuro}
              color="bg-amber-600"
              label="Risque financier"
              value={fmtEur(stats.risque)}
              detail={`${stats.withAno} ${stats.withAno > 1 ? 'sites' : 'site'} avec anomalies`}
              active={filterAnomalies}
              onClick={() =>
                setParams({ anomalies: filterAnomalies ? '' : '1', statut: '', view: '' })
              }
            />
          </div>

          {/* ── V100 — Segmentation Card (profil energie) ── */}
          <div className="grid grid-cols-3 gap-3">
            <div className="col-span-1">
              <SegmentationWidget compact onSegmentationClick={() => setShowSegModal(true)} />
            </div>
          </div>

          {/* ── Toolbar ── */}
          <div className="flex items-center gap-2 flex-wrap">
            {/* Search */}
            <div className="relative flex-1 min-w-[200px] max-w-sm">
              <Search
                size={15}
                className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400"
              />
              <input
                ref={searchRef}
                type="text"
                placeholder='Rechercher... (appuyez "/")'
                value={search}
                onChange={(e) => setParams({ q: e.target.value || '' })}
                className="w-full pl-8 pr-3 py-1.5 border border-gray-200 rounded-lg text-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white"
              />
            </div>

            {/* Filters */}
            <FilterSelect
              options={USAGE_OPTIONS}
              value={filterUsage}
              onChange={(v) => setParams({ usage: v, view: '' })}
            />
            <FilterSelect
              options={STATUT_OPTIONS}
              value={filterStatut}
              onChange={(v) => setParams({ statut: v, view: '' })}
            />

            {/* Separator */}
            <div className="w-px h-6 bg-gray-200" />

            {/* Preset views */}
            {PRESET_VIEWS.map((v) => (
              <button
                key={v.id}
                onClick={() => applyPreset(v)}
                className={`text-xs px-2.5 py-1.5 rounded-md font-medium transition whitespace-nowrap ${
                  activeView === v.id
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {v.label}
              </button>
            ))}

            {/* Sort indicator */}
            {sortCol && (
              <Tooltip text={`Tri : ${sortCol} ${sortDir}`}>
                <span className="text-[10px] text-gray-400 flex items-center gap-1">
                  <ArrowUpDown size={10} /> {sortDir === 'desc' ? '↓' : '↑'}
                </span>
              </Tooltip>
            )}
          </div>

          {/* Active filter chips */}
          {activeChips.length > 0 && (
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="text-[10px] text-gray-400 uppercase tracking-wider font-medium">
                Filtres :
              </span>
              {activeChips.map((c) => (
                <span
                  key={c.label}
                  className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 font-medium"
                >
                  {c.label}
                  <button
                    onClick={c.clear}
                    className="hover:text-blue-900"
                    aria-label={`Retirer filtre ${c.label}`}
                  >
                    <X size={10} />
                  </button>
                </span>
              ))}
              <button
                onClick={resetFilters}
                className="text-[10px] text-gray-400 hover:text-gray-600 underline ml-1"
              >
                Réinitialiser
              </button>
              <span className="ml-auto text-xs text-gray-400">{pl(total, 'resultat')}</span>
            </div>
          )}

          {/* ── Bulk actions bar ── */}
          {selectedStats && (
            <div className="flex items-center gap-3 px-3 py-2 bg-blue-600 text-white rounded-lg text-sm shadow-md">
              <span className="font-bold">{selectedStats.count}</span>
              <span className="opacity-80">{selectedStats.count > 1 ? 'sites' : 'site'}</span>
              {selectedStats.risque > 0 && (
                <span className="text-xs bg-white/20 px-2 py-0.5 rounded-full">
                  {fmtEur(selectedStats.risque)} de risque
                </span>
              )}
              <div className="flex-1" />
              <Button
                size="sm"
                variant="secondary"
                onClick={() => openActionDrawer({ sourceType: 'patrimoine' })}
                className="!bg-white !text-blue-700 !border-0 hover:!bg-blue-50"
              >
                <Plus size={13} /> Action
              </Button>
              <Button
                size="sm"
                variant="secondary"
                onClick={exportCsv}
                className="!bg-white/20 !text-white !border-0 hover:!bg-white/30"
              >
                <Download size={13} /> CSV
              </Button>
              <Button
                size="sm"
                variant="secondary"
                onClick={toggleFavorites}
                className="!bg-white/20 !text-white !border-0 hover:!bg-white/30"
              >
                <Star size={13} />
              </Button>
              <button
                onClick={() => setSelected(new Set())}
                className="p-1 rounded hover:bg-white/20"
                aria-label="Désélectionner tout"
              >
                <X size={14} />
              </button>
            </div>
          )}

          {/* ── Table ── */}
          {total === 0 ? (
            <EmptyState
              icon={Search}
              title="Aucun site ne correspond"
              text="Essayez d'autres critères ou réinitialiser les filtres."
              ctaLabel="Réinitialiser"
              onCta={resetFilters}
            />
          ) : (
            <Card id="sites-table" className="flex flex-col">
              <div
                ref={scrollRef}
                className="overflow-auto"
                style={{ maxHeight: 'calc(100vh - 340px)', minHeight: '400px' }}
              >
                <Table compact pinFirst>
                  <Thead sticky>
                    <tr>
                      <ThCheckbox
                        checked={selected.size === filtered.length && filtered.length > 0}
                        onChange={toggleSelectAll}
                      />
                      <Th className="w-10 text-center text-gray-400">#</Th>
                      <Th
                        sortable
                        sorted={sortCol === 'nom' ? sortDir : ''}
                        onSort={() => handleSort('nom')}
                        pin
                      >
                        Site
                      </Th>
                      <Th>Usage</Th>
                      <Th>Conformité</Th>
                      <Th
                        sortable
                        sorted={sortCol === 'risque_eur' ? sortDir : ''}
                        onSort={() => handleSort('risque_eur')}
                        className="text-right"
                      >
                        Risque
                      </Th>
                      <Th
                        sortable
                        sorted={sortCol === 'surface_m2' ? sortDir : ''}
                        onSort={() => handleSort('surface_m2')}
                        className="text-right"
                      >
                        Surface
                      </Th>
                      {isExpert && (
                        <Th
                          sortable
                          sorted={sortCol === 'conso_kwh_an' ? sortDir : ''}
                          onSort={() => handleSort('conso_kwh_an')}
                          className="text-right"
                        >
                          Conso
                        </Th>
                      )}
                      <Th
                        sortable
                        sorted={sortCol === 'anomalies_count' ? sortDir : ''}
                        onSort={() => handleSort('anomalies_count')}
                        className="text-right"
                      >
                        Anomalies
                      </Th>
                      <Th className="text-center">Réconc.</Th>
                      <Th className="text-center">Qualité</Th>
                      <Th className="w-8" />
                    </tr>
                  </Thead>
                  <Tbody>
                    {paddingTop > 0 && (
                      <tr className="!border-0">
                        <td
                          colSpan={colCount}
                          style={{ height: paddingTop, padding: 0, border: 'none', lineHeight: 0 }}
                        />
                      </tr>
                    )}
                    {virtualItems.map((vr) => {
                      const site = filtered[vr.index];
                      const badge = STATUT_BADGE[site.statut_conformite] || STATUT_BADGE.a_evaluer;
                      const usageColor =
                        USAGE_COLOR[site.usage] || 'bg-gray-100 text-gray-600 ring-gray-200';
                      const rank = vr.index + 1;
                      const isFav = favorites.has(site.id);
                      return (
                        <Tr
                          key={site.id}
                          selected={selected.has(site.id)}
                          className="group"
                          onClick={() => openDrawer(site)}
                        >
                          <TdCheckbox
                            checked={selected.has(site.id)}
                            onChange={() => toggleSelect(site.id)}
                          />
                          <Td className="text-center text-xs text-gray-400 font-mono tabular-nums">
                            {rank}
                          </Td>
                          <Td pin>
                            <div className="min-w-0">
                              <div className="flex items-center gap-1">
                                {isFav && (
                                  <Star
                                    size={11}
                                    className="text-amber-400 fill-amber-400 shrink-0"
                                  />
                                )}
                                <span className="font-medium text-gray-900 truncate text-sm">
                                  {site.nom}
                                </span>
                              </div>
                              <div className="text-[11px] text-gray-400 truncate leading-tight">
                                {site.adresse}, {site.code_postal} {site.ville}
                              </div>
                            </div>
                          </Td>
                          <Td>
                            <span
                              className={`capitalize text-[11px] px-2 py-0.5 rounded-md font-medium ring-1 ring-inset ${usageColor}`}
                            >
                              {site.usage}
                            </span>
                          </Td>
                          <Td>
                            <Badge status={badge.status}>{badge.label}</Badge>
                          </Td>
                          <Td className="text-right tabular-nums">
                            {site.risque_eur > 0 ? (
                              <span
                                className={`font-semibold text-sm ${site.risque_eur >= RISK_THRESHOLDS.site.crit ? 'text-red-600' : site.risque_eur >= RISK_THRESHOLDS.site.warn ? 'text-amber-600' : 'text-gray-700'}`}
                              >
                                {fmtEur(site.risque_eur)}
                              </span>
                            ) : (
                              <span className="text-gray-300">—</span>
                            )}
                          </Td>
                          <Td className="text-right text-sm text-gray-600 tabular-nums">
                            {fmtArea(site.surface_m2)}
                          </Td>
                          {isExpert && (
                            <Td className="text-right text-sm text-gray-600 tabular-nums">
                              {fmtKwh(site.conso_kwh_an)}
                            </Td>
                          )}
                          <Td className="text-right">
                            {site.anomalies_count > 0 ? (
                              <Tooltip
                                text={`${site.anomalies_count} anomalie${site.anomalies_count > 1 ? 's' : ''} détectée${site.anomalies_count > 1 ? 's' : ''}`}
                              >
                                <span
                                  className={`inline-flex items-center justify-center min-w-[22px] h-[22px] rounded-full text-[11px] font-bold ${
                                    site.anomalies_count >= ANOMALY_THRESHOLDS.critical
                                      ? 'bg-red-100 text-red-700'
                                      : 'bg-amber-100 text-amber-700'
                                  }`}
                                >
                                  {site.anomalies_count}
                                </span>
                              </Tooltip>
                            ) : (
                              <span className="text-gray-300 text-xs">0</span>
                            )}
                          </Td>
                          <Td className="text-center">
                            {(() => {
                              const rc = reconMap[site.id];
                              if (!rc) return <span className="text-gray-300">—</span>;
                              const dot =
                                rc.status === 'ok'
                                  ? 'bg-green-500'
                                  : rc.status === 'warn'
                                    ? 'bg-amber-400'
                                    : 'bg-red-500';
                              return (
                                <Tooltip text={`Réconciliation: ${rc.score}%`}>
                                  <span
                                    className={`inline-block w-2.5 h-2.5 rounded-full ${dot}`}
                                  />
                                </Tooltip>
                              );
                            })()}
                          </Td>
                          <Td className="text-center">
                            {dqMap[site.id] ? (
                              <DataQualityBadge score={dqMap[site.id].score} size="sm" />
                            ) : (
                              <span className="text-gray-300">—</span>
                            )}
                          </Td>
                          <Td>
                            <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition">
                              <Tooltip text="Créer action">
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    openActionFromDrawer(site.nom);
                                  }}
                                  className="p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-amber-600"
                                >
                                  <Lightbulb size={14} />
                                </button>
                              </Tooltip>
                              <ChevronRight size={14} className="text-gray-300" />
                            </div>
                          </Td>
                        </Tr>
                      );
                    })}
                    {paddingBottom > 0 && (
                      <tr className="!border-0">
                        <td
                          colSpan={colCount}
                          style={{
                            height: paddingBottom,
                            padding: 0,
                            border: 'none',
                            lineHeight: 0,
                          }}
                        />
                      </tr>
                    )}
                  </Tbody>
                </Table>
              </div>
              <div className="flex items-center justify-between px-4 py-2 border-t border-gray-100">
                <span className="text-xs text-gray-400">
                  {pl(total, 'site')} · Tri : {sortCol || 'defaut'}{' '}
                  {sortDir === 'desc' ? '↓' : sortDir === 'asc' ? '↑' : ''}
                </span>
                <span className="text-xs text-gray-500">
                  {total} {total > 1 ? 'sites' : 'site'}
                </span>
              </div>
            </Card>
          )}
        </div>
      )}

      {/* ── Site Detail Drawer (tabbed) ── */}
      <Drawer
        open={!!drawerSite}
        onClose={() => setDrawerSite(null)}
        title={drawerSite?.nom || 'Site'}
        wide
      >
        {drawerSite && (
          <SiteDrawerContent
            site={drawerSite}
            navigate={navigate}
            onCreateAction={() => openActionFromDrawer(drawerSite.nom)}
            initialTab={drawerInitialTab}
            orgId={scope.orgId}
          />
        )}
      </Drawer>

      {/* Action creation handled by ActionDrawerContext */}
      {showWizard && <PatrimoineWizard onClose={() => setShowWizard(false)} />}
      {showSegModal && <SegmentationQuestionnaireModal onClose={() => setShowSegModal(false)} />}
    </PageShell>
  );
}

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 *  Sub-components
 * ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */

/** Compact select (filter dropdown) */
function FilterSelect({ options, value, onChange }) {
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

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 *  SiteDrawer — tabbed, actionable
 * ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */

const DRAWER_TABS = [
  { id: 'resume', label: 'Résumé' },
  { id: 'anomalies', label: 'Anomalies' },
  { id: 'compteurs', label: 'Compteurs' },
  { id: 'actions', label: 'Actions' },
];

function SiteDrawerContent({
  site,
  navigate,
  onCreateAction,
  initialTab = 'resume',
  orgId = null,
}) {
  const [tab, setTab] = useState(initialTab);
  const badge = STATUT_BADGE[site.statut_conformite] || STATUT_BADGE.a_evaluer;
  const usageColor = USAGE_COLOR[site.usage] || 'bg-gray-100 text-gray-600 ring-gray-200';

  return (
    <div className="space-y-4">
      {/* Header: tags + key metrics */}
      <div>
        <div className="flex items-center gap-2 mb-2">
          <span
            className={`capitalize text-[11px] px-2 py-0.5 rounded-md font-medium ring-1 ring-inset ${usageColor}`}
          >
            {site.usage}
          </span>
          <Badge status={badge.status}>{badge.label}</Badge>
          {site.anomalies_count > 0 && (
            <span className="text-[11px] px-2 py-0.5 rounded-full bg-red-50 text-red-600 font-medium">
              {site.anomalies_count} anomalie{site.anomalies_count > 1 ? 's' : ''}
            </span>
          )}
        </div>
        <div className="flex items-start gap-2 text-sm text-gray-500">
          <MapPin size={13} className="text-gray-400 mt-0.5 shrink-0" />
          <span>
            {site.adresse}, {site.code_postal} {site.ville}
          </span>
        </div>
        {/* Metric pills */}
        <div className="flex items-center gap-3 mt-3">
          <MetricPill label="Risque" value={fmtEur(site.risque_eur)} warn={site.risque_eur > 0} />
          <MetricPill label="Surface" value={fmtArea(site.surface_m2)} />
          <MetricPill label="Compteurs" value={site.nb_compteurs || '—'} />
        </div>
      </div>

      {/* Tabs */}
      <Tabs tabs={DRAWER_TABS} active={tab} onChange={setTab} />

      {/* Tab: Resume */}
      {tab === 'resume' && (
        <div className="space-y-4">
          {/* Conformite block */}
          <DrawerSection title="Conformité">
            <DrawerRow label="Statut">
              <Badge status={badge.status}>{badge.label}</Badge>
            </DrawerRow>
            <DrawerRow label="Dernière évaluation">{fmtDateFR(site.derniere_evaluation)}</DrawerRow>
            <DrawerRow label="OPERAT">
              {site.operat_status ? (
                <span
                  className={`text-[11px] px-2 py-0.5 rounded-full font-medium ${
                    site.operat_status === 'verified'
                      ? 'bg-green-100 text-green-700'
                      : site.operat_status === 'submitted'
                        ? 'bg-blue-100 text-blue-700'
                        : 'bg-gray-100 text-gray-600'
                  }`}
                >
                  {site.operat_status === 'verified'
                    ? 'Vérifié'
                    : site.operat_status === 'submitted'
                      ? 'Soumis'
                      : 'Non démarré'}
                </span>
              ) : (
                '—'
              )}
            </DrawerRow>
          </DrawerSection>

          {/* Risk block */}
          <DrawerSection title="Risque">
            <DrawerRow label="Risque estime">{fmtEurFull(site.risque_eur)}</DrawerRow>
            <DrawerRow label="Anomalies">
              {site.anomalies_count > 0 ? `${site.anomalies_count}` : '0'}
            </DrawerRow>
          </DrawerSection>

          {/* Data block */}
          <DrawerSection title="Données">
            <DrawerRow label="Surface">{fmtArea(site.surface_m2)}</DrawerRow>
            <DrawerRow label="Conso annuelle">{fmtKwh(site.conso_kwh_an)}</DrawerRow>
            <DrawerRow label="Compteurs">{site.nb_compteurs || '—'}</DrawerRow>
          </DrawerSection>
        </div>
      )}

      {/* Tab: Anomalies — V65 SiteAnomalyPanel */}
      {tab === 'anomalies' && (
        <div>
          <SiteAnomalyPanel siteId={site.id} orgId={orgId} />
        </div>
      )}

      {/* Tab: Compteurs */}
      {tab === 'compteurs' && (
        <div>
          {site.nb_compteurs > 0 ? (
            <div className="space-y-2">
              <p className="text-sm text-gray-600">
                {site.nb_compteurs} compteur{site.nb_compteurs > 1 ? 's' : ''} associé
                {site.nb_compteurs > 1 ? 's' : ''} à ce site.
              </p>
              <p className="text-xs text-gray-400">
                Ouvrez la fiche site pour voir le détail de chaque compteur et ses consommations.
              </p>
            </div>
          ) : (
            <div className="text-center py-8 text-gray-400">
              <Zap size={28} className="mx-auto mb-2" />
              <p className="text-sm font-medium text-gray-600">Aucun compteur</p>
              <p className="text-xs text-gray-400">Ce site n'a pas encore de compteur rattaché.</p>
            </div>
          )}
        </div>
      )}

      {/* Tab: Actions */}
      {tab === 'actions' && (
        <div className="space-y-3">
          <DrawerActionBtn
            icon={Eye}
            color="text-blue-600"
            title="Voir la fiche site"
            desc="Details, compteurs, consommations"
            onClick={() => navigate(`/sites/${site.id}`)}
          />
          <DrawerActionBtn
            icon={ShieldCheck}
            color="text-green-600"
            title="Voir la conformité"
            desc="Décret Tertiaire, BACS, obligations"
            onClick={() => navigate('/conformite')}
          />
          <DrawerActionBtn
            icon={Lightbulb}
            color="text-amber-600"
            title="Créer une action"
            desc="Correction, amélioration, conformité"
            onClick={onCreateAction}
            primary
          />
        </div>
      )}

      {/* Always-visible primary CTA */}
      <div className="pt-2 border-t border-gray-100">
        <button
          onClick={onCreateAction}
          className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-blue-600 text-white text-sm font-semibold hover:bg-blue-700 transition"
        >
          <Lightbulb size={15} /> Créer une action pour ce site
        </button>
      </div>

      <div className="text-[10px] text-gray-400 pt-1">
        Site #{site.id} ·{' '}
        {fmtDateFR(site.derniere_evaluation) !== '—'
          ? `Maj : ${fmtDateFR(site.derniere_evaluation)}`
          : 'Pas encore évalué'}
      </div>
    </div>
  );
}

/* ── Drawer sub-components ── */

function MetricPill({ label, value, warn }) {
  return (
    <div className={`text-center px-3 py-1.5 rounded-lg ${warn ? 'bg-red-50' : 'bg-gray-50'}`}>
      <p className={`text-sm font-bold ${warn ? 'text-red-600' : 'text-gray-900'}`}>{value}</p>
      <p className="text-[9px] text-gray-400 uppercase tracking-wider">{label}</p>
    </div>
  );
}

function DrawerSection({ title, children }) {
  return (
    <div className="bg-gray-50 rounded-lg p-3 space-y-1.5">
      <h4 className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">{title}</h4>
      {children}
    </div>
  );
}

function DrawerRow({ label, children }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-gray-500">{label}</span>
      <span className="text-gray-900 font-medium">{children}</span>
    </div>
  );
}

function DrawerActionBtn({ icon: Icon, color, title, desc, onClick, primary }) {
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center gap-3 p-3 rounded-lg border text-left transition ${
        primary
          ? 'border-blue-200 bg-blue-50 hover:bg-blue-100'
          : 'border-gray-200 hover:bg-gray-50'
      }`}
    >
      <Icon size={16} className={`${color} shrink-0`} />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-800">{title}</p>
        <p className="text-[11px] text-gray-500">{desc}</p>
      </div>
      {primary ? (
        <ChevronRight size={14} className="text-blue-400" />
      ) : (
        <ExternalLink size={13} className="text-gray-300" />
      )}
    </button>
  );
}
