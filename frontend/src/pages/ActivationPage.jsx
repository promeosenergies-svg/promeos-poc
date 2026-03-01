/**
 * PROMEOS — ActivationPage V37
 * Page dediee /activation : checklist par dimension + table par site.
 */
import { useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Database, CheckCircle2, Circle, ArrowRight, Search,
} from 'lucide-react';
import { useScope } from '../contexts/ScopeContext';
import { PageShell, Card, CardBody, Button, Progress, EmptyState } from '../ui';
import { Table, Thead, Tbody, Th, Tr, Td } from '../ui';
import { buildActivationChecklist, ACTIVATION_DIMENSIONS } from '../models/dataActivationModel';
import useActivationData from '../hooks/useActivationData';

// ── Status icon inline ──────────────────────────────────────────────────────
function DimStatus({ ok }) {
  return ok
    ? <CheckCircle2 size={14} className="text-emerald-500" />
    : <Circle size={14} className="text-gray-300" />;
}

// ── Dimension filter tabs ───────────────────────────────────────────────────
const FILTER_TABS = [
  { key: 'all', label: 'Tous' },
  { key: 'patrimoine', label: 'Patrimoine' },
  { key: 'conformite', label: 'Conformit\u00e9' },
  { key: 'consommation', label: 'Consommation' },
  { key: 'facturation', label: 'Facturation' },
  { key: 'achat', label: 'Contrats' },
];

export default function ActivationPage() {
  const navigate = useNavigate();
  const [sp, setSp] = useSearchParams();
  const { scopedSites } = useScope();
  const filterDim = sp.get('dim') || 'all';

  const [siteSearch, setSiteSearch] = useState('');

  // Compute kpis from scopedSites (same formula as Cockpit.jsx L58-79)
  const kpis = useMemo(() => {
    const sites = scopedSites;
    const total = sites.length;
    const conformes = sites.filter((s) => s.statut_conformite === 'conforme').length;
    const nonConformes = sites.filter((s) => s.statut_conformite === 'non_conforme').length;
    const aRisque = sites.filter((s) => s.statut_conformite === 'a_risque').length;
    const couvertureDonnees = total > 0
      ? Math.round(sites.filter((s) => s.conso_kwh_an > 0).length / total * 100)
      : 0;
    return { total, conformes, nonConformes, aRisque, couvertureDonnees };
  }, [scopedSites]);

  const { billingSummary, purchaseSignals, contractSiteIds, loading } = useActivationData(kpis.total);

  const activation = useMemo(
    () => buildActivationChecklist({
      kpis,
      billingSummary: billingSummary || {},
      purchaseSignals,
    }),
    [kpis, billingSummary, purchaseSignals],
  );

  // Per-site activation status
  const hasBillingOrg = (billingSummary?.total_invoices ?? billingSummary?.total_eur ?? 0) > 0;

  const sitesWithStatus = useMemo(() => {
    return scopedSites.map((site) => ({
      ...site,
      _activation: {
        patrimoine: true, // site exists
        conformite: site.statut_conformite != null,
        consommation: (site.conso_kwh_an ?? 0) > 0,
        facturation: hasBillingOrg,
        achat: contractSiteIds.has(site.id),
      },
    }));
  }, [scopedSites, hasBillingOrg, contractSiteIds]);

  // Filter sites
  const filteredSites = useMemo(() => {
    let list = sitesWithStatus;

    // Filter by missing dimension
    if (filterDim !== 'all' && ACTIVATION_DIMENSIONS.includes(filterDim)) {
      list = list.filter((s) => !s._activation[filterDim]);
    }

    // Search
    if (siteSearch.trim()) {
      const q = siteSearch.toLowerCase();
      list = list.filter((s) =>
        s.nom.toLowerCase().includes(q) ||
        (s.ville || '').toLowerCase().includes(q),
      );
    }

    return list;
  }, [sitesWithStatus, filterDim, siteSearch]);

  if (loading) {
    return (
      <PageShell icon={Database} title="Activation des donn\u00e9es">
        <Card>
          <CardBody className="flex items-center justify-center gap-2 py-12 text-gray-400">
            <span className="text-sm">Chargement…</span>
          </CardBody>
        </Card>
      </PageShell>
    );
  }

  return (
    <PageShell icon={Database} title="Activation des donn\u00e9es" subtitle={`${activation.activatedCount}/${activation.totalDimensions} briques actives`}>
      {/* ── Resume par dimension ── */}
      <div className="grid grid-cols-1 sm:grid-cols-5 gap-3">
        {activation.dimensions.map((dim) => (
          <Card key={dim.key}>
            <CardBody className="p-3">
              <div className="flex items-center gap-2 mb-2">
                <DimStatus ok={dim.available} />
                <span className="text-xs font-semibold text-gray-700">{dim.label}</span>
              </div>
              <Progress value={dim.coverage} size="sm" color={dim.available ? 'blue' : 'gray'} />
              <p className="text-[10px] text-gray-400 mt-1">
                {dim.available ? dim.detail : dim.description}
              </p>
              {!dim.available && (
                <Button
                  size="xs"
                  variant="secondary"
                  className="mt-2 w-full text-xs"
                  onClick={() => navigate(dim.ctaPath)}
                >
                  {dim.ctaLabel} <ArrowRight size={12} />
                </Button>
              )}
            </CardBody>
          </Card>
        ))}
      </div>

      {/* ── Filtres ── */}
      <div className="flex items-center gap-2 flex-wrap">
        {FILTER_TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setSp(tab.key === 'all' ? {} : { dim: tab.key })}
            className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
              filterDim === tab.key
                ? 'bg-blue-100 text-blue-700'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {tab.label}
            {tab.key !== 'all' && (
              <span className="ml-1 text-gray-400">
                ({sitesWithStatus.filter((s) => !s._activation[tab.key]).length})
              </span>
            )}
          </button>
        ))}
      </div>

      {/* ── Table par site ── */}
      <Card>
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between gap-4">
          <h3 className="text-sm font-semibold text-gray-800">
            Sites ({filteredSites.length})
            {filterDim !== 'all' && (
              <span className="text-gray-400 font-normal ml-1">
                — {FILTER_TABS.find((t) => t.key === filterDim)?.label} manquante
              </span>
            )}
          </h3>
          <div className="relative w-56">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Rechercher\u2026"
              value={siteSearch}
              onChange={(e) => setSiteSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 border border-gray-300 rounded-lg text-sm placeholder:text-gray-400
                focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        {filteredSites.length === 0 ? (
          <div className="py-12">
            <EmptyState
              icon={Search}
              title="Aucun site trouv\u00e9"
              text={siteSearch ? 'Essayez un autre terme.' : 'Aucun site ne correspond au filtre.'}
              ctaLabel={siteSearch ? 'Effacer' : undefined}
              onCta={siteSearch ? () => setSiteSearch('') : undefined}
            />
          </div>
        ) : (
          <Table>
            <Thead>
              <tr>
                <Th>Site</Th>
                <Th>Ville</Th>
                <Th className="text-center">Patrimoine</Th>
                <Th className="text-center">Conformité</Th>
                <Th className="text-center">Conso</Th>
                <Th className="text-center">Facture</Th>
                <Th className="text-center">Contrat</Th>
              </tr>
            </Thead>
            <Tbody>
              {filteredSites.map((site) => (
                <Tr key={site.id} onClick={() => navigate(`/sites/${site.id}`)} className="group cursor-pointer hover:bg-blue-50/40">
                  <Td>
                    <div className="font-medium text-gray-900">{site.nom}</div>
                    <div className="text-xs text-gray-400">{site.usage}</div>
                  </Td>
                  <Td>{site.ville}</Td>
                  <Td className="text-center"><DimStatus ok={site._activation.patrimoine} /></Td>
                  <Td className="text-center"><DimStatus ok={site._activation.conformite} /></Td>
                  <Td className="text-center"><DimStatus ok={site._activation.consommation} /></Td>
                  <Td className="text-center"><DimStatus ok={site._activation.facturation} /></Td>
                  <Td className="text-center"><DimStatus ok={site._activation.achat} /></Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        )}
      </Card>
    </PageShell>
  );
}
