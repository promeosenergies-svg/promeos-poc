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
  Zap,
  ExternalLink,
  Eye,
  Lightbulb,
  X,
  ArrowUpDown,
  ChevronDown,
  PlusCircle,
  PieChart,
  FileText,
  Clock,
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
import { useToast } from '../ui';
import ErrorState from '../ui/ErrorState'; // eslint-disable-line no-unused-vars
import { useScope } from '../contexts/ScopeContext';
import { useExpertMode } from '../contexts/ExpertModeContext';
import { useActionDrawer } from '../contexts/ActionDrawerContext';
import PatrimoineWizard from '../components/PatrimoineWizard';
import SiteCreationWizard from '../components/SiteCreationWizard';
import QuickCreateSite from '../components/QuickCreateSite';
import DrawerEditSite from '../components/DrawerEditSite';
import DrawerAddCompteur from '../components/DrawerAddCompteur';
import DrawerAddContrat from '../components/DrawerAddContrat';
import SitesMap from '../components/patrimoine/SitesMap';
import PatrimoinePortfolioHealthBar from '../components/PatrimoinePortfolioHealthBar';
import PatrimoineHeatmap from '../components/PatrimoineHeatmap';
import PatrimoineRiskDistributionBar from '../components/PatrimoineRiskDistributionBar';
import SiteAnomalyPanel from '../components/SiteAnomalyPanel';
import MeterSourceBadge from '../components/MeterSourceBadge';
import SegmentationWidget from '../components/SegmentationWidget';
import SegmentationQuestionnaireModal from '../components/SegmentationQuestionnaireModal';
import {
  getPatrimoineAnomalies,
  getPortfolioReconciliation,
  patrimoineSiteMeters as _patrimoineSiteMeters,
  getSiteMetersTree,
  createSubMeter,
  getMeterBreakdown,
  getPatrimoineKpis,
  getPatrimoineContracts,
  patrimoineDeliveryPoints,
} from '../services/api';
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
import { RISK_THRESHOLDS, ANOMALY_THRESHOLDS, getStatusBadgeProps } from '../lib/constants';
import DataQualityBadge from '../components/DataQualityBadge';
import { getDataQualityPortfolio, getSiteCompleteness } from '../services/api';

/* ─── Constants ──────────────────────────────────────────── */

const ROW_HEIGHT = 52; // px — fixed row height for virtual scroll
const OVERSCAN = 10; // extra rows above/below viewport

const USAGE_OPTIONS = [
  { value: '', label: 'Usage' },
  { value: 'bureau', label: 'Bureau' },
  { value: 'commerce', label: 'Commerce' },
  { value: 'entrepot', label: 'Entrepôt' },
  { value: 'hotel', label: 'Hôtel' },
  { value: 'sante', label: 'Santé' },
  { value: 'enseignement', label: 'Enseignement' },
  { value: 'copropriete', label: 'Copropriété' },
  { value: 'collectivite', label: 'Collectivité' },
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
    filter: { statut: 'nc_risque' },
  },
  { id: 'eval', label: 'À évaluer', sort: 'nom', dir: 'asc', filter: { statut: 'a_evaluer' } },
];

/* ─── Main Component ─────────────────────────────────────── */

export default function Patrimoine() {
  const navigate = useNavigate();
  const location = useLocation();
  const [sp, setSp] = useSearchParams();
  const { scopedSites, sitesLoading, scope, org, refreshSites } = useScope();
  const { isExpert } = useExpertMode();
  const searchRef = useRef(null);
  const [dataVersion, setDataVersion] = useState(0);

  // Refresh cible apres mutation (creation, edition, enrichissement)
  const handleDataMutation = useCallback(() => {
    refreshSites();
    setDataVersion((v) => v + 1);
  }, [refreshSites]);

  // URL-synced state
  const search = sp.get('q') || '';
  const filterUsage = sp.get('usage') || '';
  const filterStatut = sp.get('statut') || '';
  const filterPortefeuille = sp.get('pf') || '';
  const filterAnomalies = sp.get('anomalies') === '1';
  const sortCol = sp.get('sort') || 'risque_eur';
  const sortDir = sp.get('dir') || 'desc';
  const activeView = sp.get('view') || '';

  const scrollRef = useRef(null);
  const [selected, setSelected] = useState(new Set());
  const { openActionDrawer } = useActionDrawer();
  const [showWizard, setShowWizard] = useState(false);
  const [showSiteWizard, setShowSiteWizard] = useState(sp.get('wizard') === 'open');
  const [showQuickCreate, setShowQuickCreate] = useState(false);
  const [showSegModal, setShowSegModal] = useState(false);
  const [viewMode, setViewMode] = useState('table');
  const [drawerSite, setDrawerSite] = useState(null);
  const [drawerInitialTab, setDrawerInitialTab] = useState('resume');

  // B2-6: Expiring contracts view
  const [expiringContracts, setExpiringContracts] = useState([]);
  const [expiringLoading, setExpiringLoading] = useState(false);

  // PDL view
  const [allDeliveryPoints, setAllDeliveryPoints] = useState([]);
  const [dpLoading, setDpLoading] = useState(false);

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
        (data.sites || []).forEach((s) => {
          m[s.site_id] = s;
        });
        setDqMap(m);
      })
      .catch(() => {});
  }, [org?.id]);

  // V-registre: KPIs patrimoine agregees — scope-aware
  const [registreKpis, setRegistreKpis] = useState(null);
  const scopedSiteIds = useMemo(() => new Set(scopedSites.map((s) => s.id)), [scopedSites]);
  useEffect(() => {
    if (!org?.id) return;
    const params = {};
    if (scope.siteId) params.site_id = scope.siteId;
    getPatrimoineKpis(params)
      .then(setRegistreKpis)
      .catch(() => {});
  }, [org?.id, scope.siteId, dataVersion]);

  // Contracts (for expiring view) — scope-aware
  const [scopedContracts, setScopedContracts] = useState([]);
  useEffect(() => {
    if (!org?.id) return;
    const params = { limit: 500 };
    if (scope.siteId) params.site_id = scope.siteId;
    getPatrimoineContracts(params)
      .then((data) => setScopedContracts(data.contracts || []))
      .catch(() => setScopedContracts([]));
  }, [org?.id, scope.siteId, dataVersion]);

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

  const HEATMAP_MAX_SITES = 10;

  // V63 — Enrichissement heatmap : anomalies par site (Promise.all, max 10 sites, guard stale)
  useEffect(() => {
    if (scopedSites.length === 0) {
      setHmTiles([]);
      setHmLoading(false);
      setHmError(null);
      return;
    }
    const sitesToFetch = scopedSites.slice(0, HEATMAP_MAX_SITES);
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

  // B2-7: Dynamic portefeuille filter options
  // B2-6: Compute expiring contracts from scopedContracts (scope-aware)
  useEffect(() => {
    if (activeView !== 'expiring') {
      setExpiringContracts([]);
      setExpiringLoading(false);
      return;
    }
    setExpiringLoading(true);
    const now = new Date();
    const horizon = 90 * 24 * 60 * 60 * 1000;
    const expiring = scopedContracts
      .filter((ct) => scopedSiteIds.has(ct.site_id))
      .filter((ct) => {
        if (!ct.end_date) return false;
        const end = new Date(ct.end_date);
        const diff = end - now;
        return diff > 0 && diff <= horizon;
      });
    // Enrich with site name
    const siteMap = {};
    scopedSites.forEach((s) => {
      siteMap[s.id] = s.nom;
    });
    expiring.forEach((ct) => {
      ct._site_nom = siteMap[ct.site_id] || `Site #${ct.site_id}`;
    });
    expiring.sort((a, b) => new Date(a.end_date) - new Date(b.end_date));
    setExpiringContracts(expiring);
    setExpiringLoading(false);
  }, [activeView, scopedContracts, scopedSites, scopedSiteIds]);

  // PDL view: fetch delivery points for all scoped sites
  useEffect(() => {
    if (activeView !== 'pdl') {
      setAllDeliveryPoints([]);
      setDpLoading(false);
      return;
    }
    let stale = false;
    setDpLoading(true);
    const siteMap = {};
    scopedSites.forEach((s) => {
      siteMap[s.id] = s.nom;
    });
    Promise.all(
      scopedSites.map((s) =>
        patrimoineDeliveryPoints(s.id)
          .then((dps) =>
            (Array.isArray(dps) ? dps : []).map((dp) => ({
              ...dp,
              _site_nom: s.nom,
              _site_id: s.id,
            }))
          )
          .catch(() => [])
      )
    ).then((results) => {
      if (stale) return;
      setAllDeliveryPoints(results.flat());
      setDpLoading(false);
    });
    return () => {
      stale = true;
    };
  }, [activeView, scopedSites]);

  const portefeuilleOptions = useMemo(() => {
    const map = new Map();
    scopedSites.forEach((s) => {
      if (s.portefeuille_id && s.portefeuille_nom) {
        map.set(String(s.portefeuille_id), s.portefeuille_nom);
      }
    });
    const opts = [{ value: '', label: 'Regroupement' }];
    for (const [id, nom] of map) opts.push({ value: id, label: nom });
    return opts;
  }, [scopedSites]);

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
    if (filterStatut === 'nc_risque') {
      r = r.filter(
        (s) => s.statut_conformite === 'non_conforme' || s.statut_conformite === 'a_risque'
      );
    } else if (filterStatut) {
      r = r.filter((s) => s.statut_conformite === filterStatut);
    }
    if (filterPortefeuille) r = r.filter((s) => String(s.portefeuille_id) === filterPortefeuille);
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
  }, [
    scopedSites,
    search,
    filterUsage,
    filterStatut,
    filterPortefeuille,
    filterAnomalies,
    sortCol,
    sortDir,
  ]);

  const total = filtered.length;

  // Virtual scroll
  const virtualizer = useVirtualizer({
    count: total,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: OVERSCAN,
  });

  // Force virtualizer re-measure when table becomes visible again
  useEffect(() => {
    if (!activeView && viewMode === 'table') {
      // Small delay to let the DOM mount before measuring
      const t = setTimeout(() => virtualizer.measure(), 50);
      return () => clearTimeout(t);
    }
  }, [activeView, viewMode]); // eslint-disable-line react-hooks/exhaustive-deps

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
      // Try exact match first, then coerce to string (handles number/string mismatch)
      const site = scopedSites.find((s) => s.id === site_id || String(s.id) === String(site_id));
      if (site) {
        setDrawerSite(site);
        setDrawerInitialTab('anomalies');
        track('portfolio_top_site_click', { site_id });
      } else if (site_id) {
        // Fallback: navigate to site compliance page instead of blocking
        navigate(`/compliance/sites/${site_id}`);
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
      label:
        filterStatut === 'nc_risque'
          ? 'NC + À risque'
          : STATUT_OPTIONS.find((o) => o.value === filterStatut)?.label || filterStatut,
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
    : `${pl(stats.total, 'site')} · ${fmtAreaCompact(stats.surface)}${registreKpis ? ` · ${registreKpis.nb_contrats_actifs} contrat${registreKpis.nb_contrats_actifs > 1 ? 's' : ''} actif${registreKpis.nb_contrats_actifs > 1 ? 's' : ''}` : ''} · ${fmtEur(stats.risque)} de risque`;

  return (
    <PageShell
      icon={Building2}
      title="Registre patrimonial & contractuel"
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
          <Button size="sm" variant="secondary" onClick={() => setShowQuickCreate(true)}>
            <Plus size={14} className="mr-1" />
            Nouveau site
          </Button>
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
            <div className="flex gap-3">
              <Button variant="secondary" size="lg" onClick={() => setShowQuickCreate(true)}>
                <Plus size={16} className="mr-2" />
                Nouveau site
              </Button>
              <Button variant="secondary" size="lg" onClick={() => setShowWizard(true)}>
                <Zap size={16} className="mr-2" />
                Demo
              </Button>
            </div>
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
          {scopedSites.length > HEATMAP_MAX_SITES && (
            <p className="text-[11px] text-gray-400 text-center -mt-2">
              Heatmap limitée à {HEATMAP_MAX_SITES} sites sur {scopedSites.length} — réduisez le
              scope pour voir tous les sites.
            </p>
          )}

          {/* ── KPI row — unified 6 cards (B2-2) ── */}
          <div className="grid grid-cols-6 gap-2">
            <KpiCardCompact
              icon={Building2}
              color="bg-blue-600"
              label="Sites actifs"
              value={stats.total}
              detail={
                registreKpis
                  ? `${registreKpis.nb_entites_juridiques} entites · ${registreKpis.nb_portefeuilles} regr.`
                  : fmtAreaCompact(stats.surface)
              }
              active={!filterStatut && !filterAnomalies && !activeView}
              onClick={() => setParams({ statut: '', anomalies: '', view: '' })}
            />
            <KpiCardCompact
              icon={Zap}
              color="bg-cyan-600"
              label="Points de livraison"
              value={registreKpis?.nb_delivery_points ?? '—'}
              detail={`${registreKpis?.nb_batiments ?? 0} bâtiment${(registreKpis?.nb_batiments ?? 0) > 1 ? 's' : ''}`}
              active={activeView === 'pdl'}
              onClick={() => setParams({ view: activeView === 'pdl' ? '' : 'pdl' })}
            />
            <KpiCardCompact
              icon={FileText}
              color="bg-violet-600"
              label="Contrats actifs"
              value={registreKpis?.nb_contrats_actifs ?? '—'}
              detail={registreKpis ? `${registreKpis.nb_contrats} total` : '—'}
              active={activeView === 'contracts'}
              onClick={() => setParams({ view: activeView === 'contracts' ? '' : 'contracts' })}
            />
            <KpiCardCompact
              icon={Clock}
              color={registreKpis?.nb_contrats_expiring_90j > 0 ? 'bg-orange-600' : 'bg-gray-400'}
              label="Expirant < 90j"
              value={registreKpis?.nb_contrats_expiring_90j ?? 0}
              detail={registreKpis?.nb_contrats_expiring_90j > 0 ? 'Action requise' : 'OK'}
              onClick={() => setParams({ view: activeView === 'expiring' ? '' : 'expiring' })}
              active={activeView === 'expiring'}
            />
            <KpiCardCompact
              icon={AlertTriangle}
              color="bg-red-600"
              label="Non conformes"
              value={stats.nc + stats.aRisque}
              detail={`${stats.nc} NC · ${stats.aRisque} à risque`}
              active={filterStatut === 'nc_risque'}
              onClick={() =>
                setParams({
                  statut: filterStatut === 'nc_risque' ? '' : 'nc_risque',
                  anomalies: '',
                  view: '',
                })
              }
            />
            <KpiCardCompact
              icon={PieChart}
              color={
                registreKpis?.completude_moyenne_pct >= 80
                  ? 'bg-emerald-600'
                  : registreKpis?.completude_moyenne_pct >= 50
                    ? 'bg-amber-600'
                    : 'bg-red-600'
              }
              label="Complétude"
              value={registreKpis ? `${registreKpis.completude_moyenne_pct}%` : '—'}
              detail={
                registreKpis?.completude_moyenne_pct >= 80
                  ? 'Complet'
                  : registreKpis?.completude_moyenne_pct >= 50
                    ? 'Partiel'
                    : 'Critique'
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
            {portefeuilleOptions.length > 2 && (
              <FilterSelect
                options={portefeuilleOptions}
                value={filterPortefeuille}
                onChange={(v) => setParams({ pf: v, view: '' })}
              />
            )}

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

            {/* View toggle: Tableau / Carte */}
            <div className="w-px h-6 bg-gray-200" />
            <button
              onClick={() => setViewMode('table')}
              className={`text-xs px-2.5 py-1.5 rounded-md font-medium transition whitespace-nowrap ${
                viewMode === 'table'
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              Tableau
            </button>
            <button
              onClick={() => setViewMode('map')}
              className={`text-xs px-2.5 py-1.5 rounded-md font-medium transition whitespace-nowrap ${
                viewMode === 'map'
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              Carte
            </button>

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
              <span className="ml-auto text-xs text-gray-400">{pl(total, 'résultat')}</span>
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

          {/* ── B2-6: Expiring contracts view ── */}
          {activeView === 'expiring' && (
            <Card>
              <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Clock size={16} className="text-orange-500" />
                  <h3 className="text-sm font-semibold text-gray-800">
                    Contrats expirant dans les 90 prochains jours
                  </h3>
                  <Badge status="warning">{expiringContracts.length}</Badge>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => navigate('/renouvellements')}
                    className="text-xs text-blue-600 hover:text-blue-800 font-medium"
                  >
                    Voir le radar renouvellements →
                  </button>
                  <button
                    onClick={() => setParams({ view: '' })}
                    className="text-xs text-gray-500 hover:text-gray-700 flex items-center gap-1"
                  >
                    <X size={12} /> Fermer
                  </button>
                </div>
              </div>
              {expiringLoading ? (
                <div className="p-8 text-center text-sm text-gray-400">Chargement...</div>
              ) : expiringContracts.length === 0 ? (
                <div className="p-8 text-center">
                  <EmptyState
                    icon={Clock}
                    title="Aucun contrat expirant"
                    text="Tous les contrats sont valides au-delà de 90 jours."
                  />
                </div>
              ) : (
                <div className="overflow-auto" style={{ maxHeight: 'calc(100vh - 340px)' }}>
                  <Table compact>
                    <Thead sticky>
                      <tr>
                        <Th>Site</Th>
                        <Th>Fournisseur</Th>
                        <Th>Énergie</Th>
                        <Th>Fin contrat</Th>
                        <Th>Jours restants</Th>
                        <Th>Indexation</Th>
                        <Th>Réf.</Th>
                        <Th className="w-10" />
                      </tr>
                    </Thead>
                    <Tbody>
                      {expiringContracts.map((ct) => {
                        const daysLeft = Math.ceil(
                          (new Date(ct.end_date) - new Date()) / (1000 * 60 * 60 * 24)
                        );
                        return (
                          <Tr
                            key={ct.id}
                            className={
                              daysLeft <= 30 ? 'bg-red-50' : daysLeft <= 60 ? 'bg-amber-50' : ''
                            }
                          >
                            <Td>
                              <button
                                onClick={() => navigate(`/sites/${ct.site_id}`)}
                                className="text-blue-600 hover:underline text-left text-xs font-medium"
                              >
                                {ct._site_nom}
                              </button>
                            </Td>
                            <Td className="text-sm font-medium">{ct.supplier_name}</Td>
                            <Td>
                              <Badge status={ct.energy_type === 'electricity' ? 'info' : 'warning'}>
                                {ct.energy_type === 'electricity'
                                  ? 'Élec'
                                  : ct.energy_type === 'gas'
                                    ? 'Gaz'
                                    : ct.energy_type}
                              </Badge>
                            </Td>
                            <Td className="text-xs">{fmtDateFR(ct.end_date)}</Td>
                            <Td>
                              <span
                                className={`text-sm font-bold ${daysLeft <= 30 ? 'text-red-600' : daysLeft <= 60 ? 'text-amber-600' : 'text-gray-700'}`}
                              >
                                {daysLeft}j
                              </span>
                            </Td>
                            <Td>
                              {ct.offer_indexation && (
                                <Badge status={ct.offer_indexation === 'fixe' ? 'info' : 'warning'}>
                                  {ct.offer_indexation}
                                </Badge>
                              )}
                            </Td>
                            <Td className="text-xs text-gray-500">
                              {ct.reference_fournisseur || '—'}
                            </Td>
                            <Td>
                              <button
                                onClick={() => navigate(`/sites/${ct.site_id}#contrats`)}
                                className="p-1 text-gray-400 hover:text-blue-600"
                                title="Voir le site"
                              >
                                <ExternalLink size={14} />
                              </button>
                            </Td>
                          </Tr>
                        );
                      })}
                    </Tbody>
                  </Table>
                </div>
              )}
            </Card>
          )}

          {/* ── PDL view ── */}
          {activeView === 'pdl' && (
            <Card>
              <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Zap size={16} className="text-cyan-500" />
                  <h3 className="text-sm font-semibold text-gray-800">Points de livraison</h3>
                  <Badge status="info">{allDeliveryPoints.length}</Badge>
                </div>
                <button
                  onClick={() => setParams({ view: '' })}
                  className="text-xs text-gray-500 hover:text-gray-700 flex items-center gap-1"
                >
                  <X size={12} /> Fermer
                </button>
              </div>
              {dpLoading ? (
                <div className="p-8 text-center text-sm text-gray-400">Chargement...</div>
              ) : allDeliveryPoints.length === 0 ? (
                <div className="p-8">
                  <EmptyState
                    icon={Zap}
                    title="Aucun PDL"
                    text="Aucun point de livraison rattaché."
                  />
                </div>
              ) : (
                <div className="overflow-auto" style={{ maxHeight: 'calc(100vh - 340px)' }}>
                  <Table compact>
                    <Thead sticky>
                      <tr>
                        <Th>Site</Th>
                        <Th>Code PDL</Th>
                        <Th>Énergie</Th>
                        <Th>Statut</Th>
                        <Th>Compteurs</Th>
                        <Th>Source</Th>
                        <Th className="w-10" />
                      </tr>
                    </Thead>
                    <Tbody>
                      {allDeliveryPoints.map((dp) => (
                        <Tr key={dp.id}>
                          <Td>
                            <button
                              onClick={() => navigate(`/sites/${dp._site_id}`)}
                              className="text-blue-600 hover:underline text-xs font-medium text-left"
                            >
                              {dp._site_nom}
                            </button>
                          </Td>
                          <Td className="font-mono text-xs">{dp.code}</Td>
                          <Td>
                            <Badge status={dp.energy_type === 'electricity' ? 'info' : 'warning'}>
                              {dp.energy_type === 'electricity'
                                ? 'Élec'
                                : dp.energy_type === 'gas'
                                  ? 'Gaz'
                                  : dp.energy_type}
                            </Badge>
                          </Td>
                          <Td>
                            <Badge status={dp.status === 'active' ? 'ok' : 'neutral'}>
                              {dp.status}
                            </Badge>
                          </Td>
                          <Td className="text-sm">{dp.compteurs_count}</Td>
                          <Td className="text-xs text-gray-500">{dp.data_source || '—'}</Td>
                          <Td>
                            <button
                              onClick={() => navigate(`/sites/${dp._site_id}`)}
                              className="p-1 text-gray-400 hover:text-blue-600"
                            >
                              <ExternalLink size={14} />
                            </button>
                          </Td>
                        </Tr>
                      ))}
                    </Tbody>
                  </Table>
                </div>
              )}
            </Card>
          )}

          {/* ── Contracts view ── */}
          {activeView === 'contracts' && (
            <Card>
              <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FileText size={16} className="text-violet-500" />
                  <h3 className="text-sm font-semibold text-gray-800">Tous les contrats</h3>
                  <Badge status="info">
                    {scopedContracts.filter((ct) => scopedSiteIds.has(ct.site_id)).length}
                  </Badge>
                </div>
                <button
                  onClick={() => setParams({ view: '' })}
                  className="text-xs text-gray-500 hover:text-gray-700 flex items-center gap-1"
                >
                  <X size={12} /> Fermer
                </button>
              </div>
              {scopedContracts.length === 0 ? (
                <div className="p-8">
                  <EmptyState icon={FileText} title="Aucun contrat" text="Aucun contrat énergie." />
                </div>
              ) : (
                <div className="overflow-auto" style={{ maxHeight: 'calc(100vh - 340px)' }}>
                  <Table compact>
                    <Thead sticky>
                      <tr>
                        <Th>Site</Th>
                        <Th>Fournisseur</Th>
                        <Th>Énergie</Th>
                        <Th>Début</Th>
                        <Th>Fin</Th>
                        <Th>Indexation</Th>
                        <Th>Statut</Th>
                        <Th>Réf.</Th>
                        <Th className="w-10" />
                      </tr>
                    </Thead>
                    <Tbody>
                      {scopedContracts
                        .filter((ct) => scopedSiteIds.has(ct.site_id))
                        .map((ct) => {
                          const siteMap = {};
                          scopedSites.forEach((s) => {
                            siteMap[s.id] = s.nom;
                          });
                          return (
                            <Tr key={ct.id}>
                              <Td>
                                <button
                                  onClick={() => navigate(`/sites/${ct.site_id}`)}
                                  className="text-blue-600 hover:underline text-xs font-medium text-left"
                                >
                                  {siteMap[ct.site_id] || `Site #${ct.site_id}`}
                                </button>
                              </Td>
                              <Td className="text-sm font-medium">{ct.supplier_name}</Td>
                              <Td>
                                <Badge
                                  status={ct.energy_type === 'electricity' ? 'info' : 'warning'}
                                >
                                  {ct.energy_type === 'electricity'
                                    ? 'Élec'
                                    : ct.energy_type === 'gas'
                                      ? 'Gaz'
                                      : ct.energy_type}
                                </Badge>
                              </Td>
                              <Td className="text-xs">
                                {ct.start_date ? fmtDateFR(ct.start_date) : '—'}
                              </Td>
                              <Td className="text-xs">
                                {ct.end_date ? fmtDateFR(ct.end_date) : '—'}
                              </Td>
                              <Td>
                                {ct.offer_indexation && (
                                  <Badge
                                    status={ct.offer_indexation === 'fixe' ? 'info' : 'warning'}
                                  >
                                    {ct.offer_indexation}
                                  </Badge>
                                )}
                              </Td>
                              <Td>
                                {ct.contract_status && (
                                  <Badge
                                    status={ct.contract_status === 'active' ? 'ok' : 'neutral'}
                                  >
                                    {ct.contract_status}
                                  </Badge>
                                )}
                              </Td>
                              <Td className="text-xs text-gray-500">
                                {ct.reference_fournisseur || '—'}
                              </Td>
                              <Td>
                                <button
                                  onClick={() => navigate(`/sites/${ct.site_id}#contrats`)}
                                  className="p-1 text-gray-400 hover:text-blue-600"
                                >
                                  <ExternalLink size={14} />
                                </button>
                              </Td>
                            </Tr>
                          );
                        })}
                    </Tbody>
                  </Table>
                </div>
              )}
            </Card>
          )}

          {/* ── Map view ── */}
          {viewMode === 'map' && !activeView && (
            <SitesMap sites={filtered} onSiteClick={(id) => navigate(`/sites/${id}`)} />
          )}

          {/* ── Table ── */}
          {viewMode === 'table' &&
            !activeView &&
            (total === 0 ? (
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
                        <Th>Type</Th>
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
                            style={{
                              height: paddingTop,
                              padding: 0,
                              border: 'none',
                              lineHeight: 0,
                            }}
                          />
                        </tr>
                      )}
                      {virtualItems.map((vr) => {
                        const site = filtered[vr.index];
                        const badge =
                          STATUT_BADGE[site.statut_conformite] || STATUT_BADGE.a_evaluer;
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
                    {pl(total, 'site')} · Tri : {sortCol || 'défaut'}{' '}
                    {sortDir === 'desc' ? '↓' : sortDir === 'asc' ? '↑' : ''}
                  </span>
                  <span className="text-xs text-gray-500">
                    {total} {total > 1 ? 'sites' : 'site'}
                  </span>
                </div>
              </Card>
            ))}
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
            onSiteUpdated={() => handleDataMutation()}
          />
        )}
      </Drawer>

      {/* Action creation handled by ActionDrawerContext */}
      {showWizard && <PatrimoineWizard onClose={() => setShowWizard(false)} />}
      {showQuickCreate && (
        <QuickCreateSite
          onClose={() => setShowQuickCreate(false)}
          onSuccess={() => handleDataMutation()}
          onAdvanced={() => setShowSiteWizard(true)}
        />
      )}
      {showSiteWizard && (
        <SiteCreationWizard
          onClose={() => setShowSiteWizard(false)}
          onSuccess={() => handleDataMutation()}
        />
      )}
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

/* ── SiteMetersTab — tree view with sub-meters (Step 26) ── */
function SiteMetersTab({ siteId, count: _count }) {
  const [meters, setMeters] = useState(null);
  const [expanded, setExpanded] = useState({});
  const [addingTo, setAddingTo] = useState(null);
  const [newName, setNewName] = useState('');
  const [breakdown, setBreakdown] = useState({});
  const [metersError, setMetersError] = useState(null);
  const toast = useToast();

  const reload = useCallback(() => {
    if (siteId) {
      setMetersError(null);
      getSiteMetersTree(siteId)
        .then((data) => setMeters(data.meters || []))
        .catch(() => {
          setMeters([]);
          setMetersError('Impossible de charger les compteurs.');
        });
    }
  }, [siteId]);

  useEffect(() => {
    reload();
  }, [reload]);

  const toggleExpand = (id) => setExpanded((prev) => ({ ...prev, [id]: !prev[id] }));

  const handleAddSub = async (parentId) => {
    if (!newName.trim()) return;
    try {
      await createSubMeter(parentId, { name: newName.trim() });
      setNewName('');
      setAddingTo(null);
      toast('Sous-compteur ajouté', 'success');
      reload();
    } catch {
      toast('Échec de l\u2019ajout du sous-compteur', 'error');
    }
  };

  const loadBreakdown = async (meterId) => {
    if (breakdown[meterId]) return;
    try {
      const data = await getMeterBreakdown(meterId);
      setBreakdown((prev) => ({ ...prev, [meterId]: data }));
    } catch {
      setBreakdown((prev) => ({ ...prev, [meterId]: { error: true } }));
      toast('Répartition indisponible', 'warning');
    }
  };

  if (meters === null) {
    return <p className="text-sm text-gray-400 animate-pulse py-4">Chargement des compteurs…</p>;
  }

  if (metersError) {
    return (
      <div className="text-center py-6 text-gray-400">
        <AlertTriangle size={24} className="mx-auto mb-2 text-amber-400" />
        <p className="text-sm font-medium text-gray-600">{metersError}</p>
        <button onClick={reload} className="mt-2 text-xs text-blue-600 hover:underline">
          Réessayer
        </button>
      </div>
    );
  }

  if (meters.length === 0) {
    return (
      <div className="text-center py-8 text-gray-400">
        <Zap size={28} className="mx-auto mb-2" />
        <p className="text-sm font-medium text-gray-600">Aucun compteur</p>
        <p className="text-xs text-gray-400">Ce site n'a pas encore de compteur rattaché.</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <p className="text-sm text-gray-600">
        {meters.length} compteur{meters.length > 1 ? 's' : ''} associé{meters.length > 1 ? 's' : ''}{' '}
        à ce site.
      </p>
      {meters.map((m) => {
        const hasSubs = m.sub_meters && m.sub_meters.length > 0;
        const isExpanded = expanded[m.id];
        const bd = breakdown[m.id];

        return (
          <div key={m.id} className="rounded-lg border border-gray-100 overflow-hidden">
            {/* Principal meter row */}
            <div className="flex items-center gap-2 px-3 py-2 bg-gray-50">
              {hasSubs ? (
                <button
                  onClick={() => {
                    toggleExpand(m.id);
                    if (!isExpanded) loadBreakdown(m.id);
                  }}
                  className="p-0.5 hover:bg-gray-200 rounded"
                >
                  {isExpanded ? (
                    <ChevronDown size={14} className="text-gray-500" />
                  ) : (
                    <ChevronRight size={14} className="text-gray-500" />
                  )}
                </button>
              ) : (
                <Zap size={14} className="text-gray-400 shrink-0" />
              )}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-800 truncate">
                  {m.name || m.numero_serie || m.meter_id}
                </p>
                <p className="text-[11px] text-gray-400">
                  {m.type_compteur || m.energy_vector || '—'}
                  {hasSubs
                    ? ` · ${m.sub_meters.length} sous-compteur${m.sub_meters.length > 1 ? 's' : ''}`
                    : ''}
                </p>
              </div>
              <MeterSourceBadge source={m.source} />
              {m.source === 'meter' && (
                <button
                  onClick={() => setAddingTo(addingTo === m.id ? null : m.id)}
                  title="Ajouter sous-compteur"
                  className="p-1 hover:bg-gray-200 rounded text-gray-400 hover:text-blue-600"
                >
                  <PlusCircle size={14} />
                </button>
              )}
            </div>

            {/* Sub-meters */}
            {isExpanded && hasSubs && (
              <div className="border-t border-gray-100">
                {m.sub_meters.map((sm) => (
                  <div
                    key={sm.id}
                    className="flex items-center gap-2 px-3 py-1.5 pl-8 bg-white border-b border-gray-50 last:border-b-0"
                  >
                    <Zap size={12} className="text-blue-400 shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-gray-700 truncate">
                        {sm.name || sm.meter_id}
                      </p>
                    </div>
                    {bd &&
                      bd.sub_meters &&
                      (() => {
                        const detail = bd.sub_meters.find((d) => d.id === sm.id);
                        return detail ? (
                          <span className="text-[10px] text-gray-400">{detail.pct_of_total}%</span>
                        ) : null;
                      })()}
                  </div>
                ))}
                {/* Breakdown delta */}
                {bd && bd.delta_kwh > 0 && (
                  <div className="flex items-center gap-2 px-3 py-1.5 pl-8 bg-amber-50 text-amber-700">
                    <PieChart size={12} className="shrink-0" />
                    <span className="text-[11px] font-medium">
                      {bd.delta_label} : {bd.delta_pct}% ({fmtKwh(Math.round(bd.delta_kwh))})
                    </span>
                  </div>
                )}
              </div>
            )}

            {/* Add sub-meter form */}
            {addingTo === m.id && (
              <div className="flex items-center gap-2 px-3 py-2 bg-blue-50 border-t border-blue-100">
                <input
                  type="text"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="Nom du sous-compteur"
                  className="flex-1 text-xs px-2 py-1 rounded border border-blue-200 focus:outline-none focus:ring-1 focus:ring-blue-400"
                  onKeyDown={(e) => e.key === 'Enter' && handleAddSub(m.id)}
                />
                <button
                  onClick={() => handleAddSub(m.id)}
                  className="text-xs px-2 py-1 bg-blue-600 text-white rounded hover:bg-blue-700"
                >
                  Ajouter
                </button>
                <button
                  onClick={() => {
                    setAddingTo(null);
                    setNewName('');
                  }}
                  className="text-xs px-2 py-1 text-gray-500 hover:text-gray-700"
                >
                  Annuler
                </button>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

const DRAWER_TABS = [
  { id: 'resume', label: 'Résumé' },
  { id: 'anomalies', label: 'Anomalies' },
  { id: 'compteurs', label: 'Compteurs' },
  { id: 'actions', label: 'Actions' },
];

// ── Completude actionnable ────────────────────────────────────────────────
const COMPLETUDE_ACTIONS = [
  {
    key: 'delivery_point',
    label: 'Ajouter un compteur (PRM/PCE)',
    badge: 'Facturation · Achat',
    color: 'text-violet-600 bg-violet-50',
    action: 'add_compteur',
    hint: 'Le point de livraison sera cree automatiquement',
  },
  {
    key: 'contrat_actif',
    label: 'Ajouter un contrat energie',
    badge: 'Achat · Facturation',
    color: 'text-blue-600 bg-blue-50',
    action: 'add_contrat',
  },
  {
    key: 'surface',
    label: 'Renseigner la surface du site',
    badge: 'Conformite',
    color: 'text-amber-600 bg-amber-50',
    action: 'edit_site',
  },
  {
    key: 'siret',
    label: 'Completer les informations etablissement',
    badge: 'OPERAT',
    color: 'text-emerald-600 bg-emerald-50',
    action: 'edit_site',
  },
  {
    key: 'coordonnees',
    label: 'Localiser le site (GPS)',
    badge: 'Cartographie',
    color: 'text-cyan-600 bg-cyan-50',
    action: 'edit_site',
  },
];

function SiteCompletude({ siteId, onAction, refreshKey }) {
  const [data, setData] = useState(null);
  useEffect(() => {
    getSiteCompleteness(siteId)
      .then(setData)
      .catch(() => {});
  }, [siteId, refreshKey]);

  if (!data || data.score >= 80) return null;

  const actions = COMPLETUDE_ACTIONS.filter((a) => data.missing.includes(a.key));
  if (actions.length === 0) return null;

  const pct = data.score;
  return (
    <div className="rounded-lg border border-blue-100 bg-blue-50/40 p-3 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-800">Completude du site</span>
        <span className="text-xs font-semibold text-blue-700">
          {data.filled}/{data.total}
        </span>
      </div>
      {/* Progress bar */}
      <div className="h-1.5 bg-blue-100 rounded-full overflow-hidden">
        <div
          className="h-full bg-blue-600 rounded-full transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
      {/* Action list */}
      <ul className="space-y-1.5">
        {actions.map((a) => (
          <li key={a.key}>
            {a.action ? (
              <button
                type="button"
                onClick={() => onAction?.(a.action)}
                className="w-full flex items-center justify-between text-sm px-2 py-1.5 -mx-2 rounded-md hover:bg-blue-50 cursor-pointer group transition"
              >
                <span className="text-gray-700 group-hover:text-blue-700">{a.label}</span>
                <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${a.color}`}>
                  {a.badge}
                </span>
              </button>
            ) : (
              <div className="flex flex-col gap-0.5">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-500">{a.label}</span>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${a.color}`}>
                    {a.badge}
                  </span>
                </div>
                {a.hint && <p className="text-[11px] text-gray-400 pl-0.5">{a.hint}</p>}
              </div>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

function SiteDrawerContent({
  site,
  navigate,
  onCreateAction,
  initialTab = 'resume',
  orgId = null,
  onSiteUpdated = null,
}) {
  const [tab, setTab] = useState(initialTab);
  const [inlineForm, setInlineForm] = useState(null); // 'edit_site' | null
  const [refreshKey, setRefreshKey] = useState(0);
  const badge = STATUT_BADGE[site.statut_conformite] || STATUT_BADGE.a_evaluer;
  const usageColor = USAGE_COLOR[site.usage] || 'bg-gray-100 text-gray-600 ring-gray-200';

  // Si un formulaire inline est actif, il remplace tout le contenu
  if (inlineForm === 'edit_site') {
    return (
      <DrawerEditSite
        site={site}
        orgId={orgId}
        onBack={() => setInlineForm(null)}
        onSuccess={() => {
          setInlineForm(null);
          setRefreshKey((k) => k + 1);
          onSiteUpdated?.();
        }}
      />
    );
  }
  if (inlineForm === 'add_compteur') {
    return (
      <DrawerAddCompteur
        siteId={site.id}
        onBack={() => setInlineForm(null)}
        onSuccess={() => {
          setInlineForm(null);
          setRefreshKey((k) => k + 1);
          setTab('compteurs');
          onSiteUpdated?.();
        }}
      />
    );
  }
  if (inlineForm === 'add_contrat') {
    return (
      <DrawerAddContrat
        siteId={site.id}
        onBack={() => setInlineForm(null)}
        onSuccess={() => {
          setInlineForm(null);
          setRefreshKey((k) => k + 1);
          onSiteUpdated?.();
        }}
      />
    );
  }

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
          {/* Completude actionnable */}
          <SiteCompletude
            siteId={site.id}
            onAction={(action) => setInlineForm(action)}
            refreshKey={refreshKey}
          />

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
                <span className="text-[11px] px-2 py-0.5 rounded-full font-medium bg-gray-100 text-gray-600">
                  Non démarré
                </span>
              )}
            </DrawerRow>
          </DrawerSection>

          {/* Risk block */}
          <DrawerSection title="Risque">
            <DrawerRow label="Risque estimé">{fmtEurFull(site.risque_eur)}</DrawerRow>
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
        <div className="space-y-3">
          <button
            type="button"
            onClick={() => setInlineForm('add_compteur')}
            className="w-full flex items-center justify-center gap-1.5 px-3 py-2 text-sm font-medium text-blue-700 bg-blue-50 rounded-lg hover:bg-blue-100 transition"
          >
            + Ajouter un compteur
          </button>
          <SiteMetersTab siteId={site.id} count={site.nb_compteurs} />
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
