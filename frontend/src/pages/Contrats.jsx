/**
 * PROMEOS — Contrats V2 Page
 * /contrats — Liste Cadre+Annexe avec KPIs, filtres, panels, wizard.
 */
import { useState, useEffect, useMemo, useCallback } from 'react';
import { FileText, Download, Plus, Search } from 'lucide-react';
import { PageShell, Badge as _Badge, Button, EmptyState, ErrorState } from '../ui';
import { SkeletonTable } from '../ui/Skeleton';
import { listCadres, getCadreKpis } from '../services/api';

import ContractKpiStrip from '../components/contracts/ContractKpiStrip';
import ContractCadrePanel from '../components/contracts/ContractCadrePanel';
import ContractAnnexePanel from '../components/contracts/ContractAnnexePanel';
import ContractWizard from '../components/contracts/ContractWizard';
import ContratsSol from './ContratsSol';

/* ── Status badges ── */
const STATUS_CFG = {
  active: { cls: 'bg-emerald-50 text-emerald-700', dot: 'bg-emerald-500', label: 'Actif' },
  expiring: { cls: 'bg-amber-50 text-amber-700', dot: 'bg-amber-500', label: 'Expire bientot' },
  expired: { cls: 'bg-red-50 text-red-700', dot: 'bg-red-500', label: 'Expire' },
  draft: { cls: 'bg-gray-50 text-gray-500', dot: 'bg-gray-400', label: 'Brouillon' },
};

const CHIPS = [
  { key: 'all', label: 'Tous' },
  { key: 'cadre', label: 'Cadre' },
  { key: 'annexes', label: 'Annexes' },
  { key: 'active', label: 'Actifs' },
  { key: 'expiring', label: 'Expirent bientot' },
  { key: 'expired', label: 'Expires' },
];

const PRICING_PILLS = {
  fixe: { cls: 'bg-blue-100 text-blue-800', label: 'Fixe' },
  fixe_hors_acheminement: { cls: 'bg-amber-100 text-amber-800', label: 'Fixe hors achemin.' },
  indexe_trve: { cls: 'bg-purple-100 text-purple-800', label: 'Indexe TRVE' },
  indexe_peg: { cls: 'bg-purple-100 text-purple-800', label: 'Indexe PEG' },
  indexe_spot: { cls: 'bg-purple-100 text-purple-800', label: 'Indexe spot' },
  indexe: { cls: 'bg-purple-100 text-purple-800', label: 'Indexe' },
  hybride: { cls: 'bg-teal-100 text-teal-800', label: 'Hybride' },
};

export default function Contrats() {
  const [cadres, setCadres] = useState([]);
  const [kpis, setKpis] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [chipFilter, setChipFilter] = useState('all');

  // Panels
  const [cadrePanel, setCadrePanel] = useState(null);
  const [annexePanel, setAnnexePanel] = useState(null);
  const [annexeCadreId, setAnnexeCadreId] = useState(null);
  const [wizardOpen, setWizardOpen] = useState(false);

  const fetchData = useCallback(() => {
    setLoading(true);
    setError(null);
    Promise.all([listCadres(), getCadreKpis()])
      .then(([c, k]) => {
        setCadres(c || []);
        setKpis(k || {});
      })
      .catch(() => {
        setError('Impossible de charger les contrats. Verifiez votre connexion et reessayez.');
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Build flat rows: cadre + indented annexes
  const rows = useMemo(() => {
    const result = [];
    for (const c of cadres) {
      result.push({ type: 'cadre', data: c });
      for (const a of c.annexes || []) {
        result.push({ type: 'annexe', data: a, cadre: c });
      }
    }
    return result;
  }, [cadres]);

  // Filter
  const filtered = useMemo(() => {
    let list = rows;
    if (chipFilter === 'cadre') list = list.filter((r) => r.type === 'cadre');
    if (chipFilter === 'annexes') list = list.filter((r) => r.type === 'annexe');
    if (chipFilter === 'active')
      list = list.filter((r) => (r.data.status || r.cadre?.status) === 'active');
    if (chipFilter === 'expiring')
      list = list.filter((r) => (r.data.status || r.cadre?.status) === 'expiring');
    if (chipFilter === 'expired')
      list = list.filter((r) => (r.data.status || r.cadre?.status) === 'expired');

    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter((r) => {
        const d = r.data;
        return (
          (d.supplier_name || '').toLowerCase().includes(q) ||
          (d.contract_ref || '').toLowerCase().includes(q) ||
          (d.site_name || '').toLowerCase().includes(q) ||
          (d.annexe_ref || '').toLowerCase().includes(q)
        );
      });
    }
    return list;
  }, [rows, chipFilter, search]);

  // Count
  const totalCadres = cadres.length;
  const totalAnnexes = cadres.reduce((s, c) => s + (c.annexes?.length || 0), 0);

  const openAnnexePanel = (annexeId, cadreId) => {
    setAnnexeCadreId(cadreId);
    setAnnexePanel(annexeId);
    setCadrePanel(null);
  };

  // Escape key
  useEffect(() => {
    const handler = (e) => {
      if (e.key === 'Escape') {
        setCadrePanel(null);
        setAnnexePanel(null);
        setWizardOpen(false);
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, []);

  return (
    <PageShell hideHeader>
      {/* Lot 2 Phase 3 : rendu Pattern B Sol en haut, panels legacy
          préservés ci-dessous pour drill-down. */}
      <ContratsSol
        cadres={cadres}
        loading={loading}
        onOpenCadre={(id) => {
          setAnnexePanel(null);
          setCadrePanel(id);
        }}
        onOpenAnnexe={(annexeId, cadreId) => openAnnexePanel(annexeId, cadreId)}
        onOpenWizard={() => setWizardOpen(true)}
      />

      {/* Panels drawer legacy préservés */}
      {cadrePanel && (
        <ContractCadrePanel
          cadreId={cadrePanel}
          onClose={() => setCadrePanel(null)}
          onOpenAnnexe={(annexeId) => openAnnexePanel(annexeId, cadrePanel)}
        />
      )}
      {annexePanel && (
        <ContractAnnexePanel
          cadreId={annexeCadreId}
          annexeId={annexePanel}
          onClose={() => setAnnexePanel(null)}
          onOpenCadre={() => {
            setAnnexePanel(null);
            setCadrePanel(annexeCadreId);
          }}
        />
      )}

      {/* Wizard */}
      <ContractWizard
        open={wizardOpen}
        onClose={() => setWizardOpen(false)}
        onCreated={fetchData}
      />

      {/* Error state legacy (si API down) */}
      {error && (
        <div className="mt-4">
          <ErrorState message={error} onRetry={fetchData} />
        </div>
      )}

      {/* Legacy body — désactivé (Lot 2 Phase 3). Rollback rapide via
          toggle `{false &&}` en cas de régression démo pilote. */}
      {false && (
        <div>
          <div className="text-xs text-gray-400 mb-1.5">
            <span className="text-blue-600">PROMEOS</span> /{' '}
            <span className="text-blue-600">Patrimoine</span> / <b>Contrats</b>
          </div>
      <div className="flex items-start justify-between mb-4">
        <div>
          <h1 className="text-xl font-extrabold tracking-tight flex items-center gap-2.5">
            Contrats energie
            <span className="text-[10px] font-bold bg-blue-50 text-blue-600 px-2.5 py-1 rounded-full">
              {totalCadres} cadre · {totalAnnexes} annexes
            </span>
          </h1>
          <div className="text-xs text-gray-400 mt-0.5">
            Cadre (entite) + annexes site · Heritage/override · Elec & Gaz · Import CSV/PDF
          </div>
        </div>
        <div className="flex gap-2">
          <Button size="sm" onClick={() => setWizardOpen(true)}>
            <Download size={12} className="mr-1" />
            Importer
          </Button>
          <Button size="sm">
            <Download size={12} className="mr-1" />
            Export
          </Button>
          <Button size="sm" variant="primary" onClick={() => setWizardOpen(true)}>
            <Plus size={12} className="mr-1" />
            Nouveau contrat
          </Button>
        </div>
      </div>

      {/* KPI Strip */}
      <ContractKpiStrip kpis={kpis} />

      {/* Toolbar */}
      <div className="flex gap-2 mb-3 flex-wrap items-center">
        <div className="flex items-center gap-2 bg-white border border-gray-200 rounded-lg px-3 py-1.5 flex-shrink-0 w-[280px] focus-within:border-blue-500 focus-within:shadow-sm transition">
          <Search size={14} className="text-gray-400" />
          <input
            className="border-none outline-none text-xs w-full bg-transparent"
            placeholder="Fournisseur, site, reference..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        {CHIPS.map((c) => (
          <button
            key={c.key}
            onClick={() => setChipFilter(c.key)}
            className={`px-3 py-1 rounded-full text-[11px] font-semibold border transition whitespace-nowrap ${chipFilter === c.key ? 'bg-blue-50 border-blue-500 text-blue-600' : 'bg-white border-gray-200 text-gray-400 hover:border-blue-400 hover:text-blue-500'}`}
          >
            {c.label}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
        {loading ? (
          <SkeletonTable rows={6} cols={9} />
        ) : error ? (
          <ErrorState message={error} onRetry={fetchData} />
        ) : filtered.length === 0 && (search.trim() || chipFilter !== 'all') ? (
          <EmptyState
            icon={Search}
            title="Aucun contrat correspondant"
            text="Aucun resultat pour ces criteres de recherche. Modifiez votre filtre ou votre recherche."
            ctaLabel="Reinitialiser"
            onCta={() => {
              setSearch('');
              setChipFilter('all');
            }}
          />
        ) : filtered.length === 0 ? (
          <EmptyState
            icon={FileText}
            title="Aucun contrat"
            text="Creez votre premier contrat cadre"
          />
        ) : (
          <table className="w-full border-collapse">
            <thead>
              <tr className="bg-gray-50">
                <th className="text-left p-2.5 text-[9px] font-bold text-gray-400 uppercase tracking-wider border-b whitespace-nowrap">
                  Fournisseur / Ref
                </th>
                <th className="text-left p-2.5 text-[9px] font-bold text-gray-400 uppercase tracking-wider border-b whitespace-nowrap w-[70px]">
                  Niveau
                </th>
                <th className="text-left p-2.5 text-[9px] font-bold text-gray-400 uppercase tracking-wider border-b whitespace-nowrap w-[55px]">
                  Energie
                </th>
                <th className="text-left p-2.5 text-[9px] font-bold text-gray-400 uppercase tracking-wider border-b whitespace-nowrap">
                  Site(s)
                </th>
                <th className="text-left p-2.5 text-[9px] font-bold text-gray-400 uppercase tracking-wider border-b whitespace-nowrap">
                  Modele prix
                </th>
                <th className="text-left p-2.5 text-[9px] font-bold text-gray-400 uppercase tracking-wider border-b whitespace-nowrap">
                  Fin contrat
                </th>
                <th className="text-left p-2.5 text-[9px] font-bold text-gray-400 uppercase tracking-wider border-b whitespace-nowrap">
                  Statut
                </th>
                <th className="text-right p-2.5 text-[9px] font-bold text-gray-400 uppercase tracking-wider border-b whitespace-nowrap">
                  €/MWh
                </th>
                <th className="text-right p-2.5 text-[9px] font-bold text-gray-400 uppercase tracking-wider border-b whitespace-nowrap">
                  Vol MWh/an
                </th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((row, _i) => {
                const isCadre = row.type === 'cadre';
                const d = row.data;
                const cadreData = row.cadre;
                const st = STATUS_CFG[d.status] || STATUS_CFG.active;
                const pricingPill = PRICING_PILLS[d.pricing_model] || (isCadre ? null : null);
                const isExpired = d.status === 'expired';

                return (
                  <tr
                    key={`${row.type}-${d.id}`}
                    className={`border-b border-gray-50 transition cursor-pointer hover:bg-blue-50/30 ${isCadre ? 'bg-purple-50/20' : ''} ${isExpired ? 'opacity-40' : ''}`}
                    onClick={() => {
                      if (isCadre) {
                        setCadrePanel(d.id);
                        setAnnexePanel(null);
                      } else {
                        openAnnexePanel(d.id, cadreData?.id);
                      }
                    }}
                  >
                    {/* Fournisseur / Ref */}
                    <td className="p-2.5 text-xs">
                      {isCadre ? (
                        <div>
                          <div className="font-semibold">{d.supplier_name}</div>
                          <div className="text-[11px] text-gray-400">{d.contract_ref}</div>
                        </div>
                      ) : (
                        <div className="pl-4 text-gray-500">
                          <span className="text-gray-300 mr-1">└</span>
                          {d.annexe_ref || `ANX-${d.id}`}
                        </div>
                      )}
                    </td>

                    {/* Niveau */}
                    <td className="p-2.5">
                      <span
                        className={`inline-flex px-2 py-0.5 rounded text-[10px] font-bold ${isCadre ? 'bg-purple-50 text-purple-700' : 'bg-blue-50 text-blue-600'}`}
                      >
                        {isCadre ? 'Cadre' : 'Annexe'}
                      </span>
                    </td>

                    {/* Energie */}
                    <td className="p-2.5 text-xs font-semibold">
                      {isCadre && (d.energy_type === 'elec' ? '⚡ Elec' : '🔵 Gaz')}
                    </td>

                    {/* Site(s) */}
                    <td className="p-2.5 text-xs">
                      {isCadre ? (
                        <span>
                          <b>
                            {d.nb_annexes} site{d.nb_annexes > 1 ? 's' : ''}
                          </b>
                          {d.annexes?.length > 0 &&
                            ` ${d.annexes
                              .slice(0, 3)
                              .map((a) => a.site_name)
                              .join(', ')}`}
                        </span>
                      ) : (
                        d.site_name
                      )}
                    </td>

                    {/* Modele prix */}
                    <td className="p-2.5">
                      {isCadre && pricingPill ? (
                        <span
                          className={`inline-flex px-2 py-0.5 rounded text-[10px] font-bold ${pricingPill.cls}`}
                        >
                          {pricingPill.label}
                        </span>
                      ) : !isCadre ? (
                        d.has_price_override ? (
                          <span>
                            <span className="inline-flex px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800">
                              Fixe
                            </span>
                            <span className="ml-1 text-[8px] bg-amber-100 text-amber-800 px-1 py-0.5 rounded font-bold align-middle">
                              override
                            </span>
                          </span>
                        ) : (
                          <span className="text-[10px] italic text-gray-400 bg-gray-50 px-2 py-0.5 rounded">
                            herite cadre
                          </span>
                        )
                      ) : null}
                    </td>

                    {/* Fin contrat */}
                    <td className="p-2.5 text-xs">
                      {isCadre && d.end_date ? (
                        <div>
                          <b>{fmtDate(d.end_date)}</b>
                          {d.days_to_expiry != null && d.days_to_expiry <= 90 && (
                            <div className="text-[10px] text-amber-600">{d.days_to_expiry}j</div>
                          )}
                        </div>
                      ) : !isCadre && d.end_date ? (
                        <div>
                          <b>{fmtDate(d.end_date)}</b>
                        </div>
                      ) : (
                        <span className="text-gray-300">—</span>
                      )}
                    </td>

                    {/* Statut */}
                    <td className="p-2.5">
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold ${st.cls}`}
                      >
                        <span className={`w-1.5 h-1.5 rounded-full ${st.dot}`} />
                        {st.label}
                      </span>
                    </td>

                    {/* €/MWh */}
                    <td className="p-2.5 text-right text-xs font-bold tabular-nums">
                      {isCadre ? d.avg_price_eur_mwh || '—' : d.volume_mwh ? '—' : '—'}
                    </td>

                    {/* Vol MWh/an */}
                    <td className="p-2.5 text-right text-xs tabular-nums">
                      {isCadre ? d.total_volume_mwh || '—' : d.volume_mwh || '—'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}

        {/* Pagination info */}
        <div className="flex justify-between p-2.5 text-[11px] text-gray-400">
          <span>
            {totalCadres} cadre · {totalAnnexes} annexes — Page 1/1
          </span>
        </div>
      </div>

      {/* Panels */}
      {cadrePanel && (
        <ContractCadrePanel
          cadreId={cadrePanel}
          onClose={() => setCadrePanel(null)}
          onOpenAnnexe={(annexeId) => openAnnexePanel(annexeId, cadrePanel)}
        />
      )}
      {annexePanel && (
        <ContractAnnexePanel
          cadreId={annexeCadreId}
          annexeId={annexePanel}
          onClose={() => setAnnexePanel(null)}
          onOpenCadre={() => {
            setAnnexePanel(null);
            setCadrePanel(annexeCadreId);
          }}
        />
      )}

      {/* Wizard */}
      <ContractWizard
        open={wizardOpen}
        onClose={() => setWizardOpen(false)}
        onCreated={fetchData}
      />
        </div>
      )}
    </PageShell>
  );
}

// eslint-disable-next-line no-unused-vars
function fmtDate(d) {
  if (!d) return '—';
  try {
    return new Date(d).toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    });
  } catch {
    return d;
  }
}
