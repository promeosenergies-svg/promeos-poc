/**
 * PROMEOS — V97 Portfolio Reconciliation Triage Page
 * /portfolio-reconciliation
 * Triage table with status filters, bulk actions, CSV export.
 */
import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ShieldCheck,
  Download,
  Search,
  Filter,
  CheckCircle,
  AlertTriangle,
  XCircle,
} from 'lucide-react';
import { Card, Badge, Button, PageShell, EmptyState } from '../ui';
import { Table, Thead, Tbody, Th, Tr, Td } from '../ui';
import { SkeletonTable } from '../ui/Skeleton';
import { useScope } from '../contexts/ScopeContext';
import { getPortfolioReconciliation, getPortfolioReconciliationCsv } from '../services/api';

const STATUS_CFG = {
  ok: { icon: CheckCircle, color: 'text-green-600', badge: 'success', label: 'OK' },
  warn: { icon: AlertTriangle, color: 'text-amber-500', badge: 'warning', label: 'Attention' },
  fail: { icon: XCircle, color: 'text-red-600', badge: 'error', label: 'Incomplet' },
};

export default function PortfolioReconciliationPage() {
  const navigate = useNavigate();
  const { sitesLoading } = useScope();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');

  useEffect(() => {
    setLoading(true);
    getPortfolioReconciliation()
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    if (!data?.sites) return [];
    let list = data.sites;
    if (filter !== 'all') list = list.filter((s) => s.status === filter);
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter((s) => s.nom?.toLowerCase().includes(q) || String(s.site_id).includes(q));
    }
    return list.sort((a, b) => a.score - b.score);
  }, [data, filter, search]);

  const handleExportCsv = async () => {
    try {
      const blob = await getPortfolioReconciliationCsv();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'portfolio_reconciliation.csv';
      a.click();
      window.URL.revokeObjectURL(url);
    } catch {
      /* ignore */
    }
  };

  return (
    <PageShell
      icon={ShieldCheck}
      title="Réconciliation Portefeuille"
      subtitle="Triage et résolution des écarts de réconciliation"
      actions={
        <Button variant="outline" onClick={handleExportCsv}>
          <Download size={14} className="mr-1" /> Exporter CSV
        </Button>
      }
    >
      {/* Stats bar */}
      {data?.stats && (
        <div className="flex gap-4 mb-4">
          {['ok', 'warn', 'fail'].map((st) => {
            const cfg = STATUS_CFG[st];
            const Icon = cfg.icon;
            return (
              <button
                key={st}
                onClick={() => setFilter(filter === st ? 'all' : st)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition ${
                  filter === st
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 bg-white hover:bg-gray-50'
                }`}
              >
                <Icon size={16} className={cfg.color} />
                <span className="text-sm font-bold">{data.stats[st]}</span>
                <span className="text-xs text-gray-500">{cfg.label}</span>
              </button>
            );
          })}
          <div className="flex items-center gap-2 px-4 py-2 bg-gray-50 rounded-lg">
            <span className="text-sm font-bold text-gray-700">{data.stats.total}</span>
            <span className="text-xs text-gray-500">Total</span>
          </div>
        </div>
      )}

      {/* Search */}
      <div className="flex items-center gap-3 mb-4">
        <div className="relative flex-1 max-w-md">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Rechercher un site..."
            className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        {filter !== 'all' && (
          <button
            onClick={() => setFilter('all')}
            className="text-xs text-blue-600 hover:underline flex items-center gap-1"
          >
            <Filter size={12} /> Tout afficher
          </button>
        )}
      </div>

      {/* Table */}
      {loading || sitesLoading ? (
        <SkeletonTable rows={8} cols={4} />
      ) : !data || filtered.length === 0 ? (
        <EmptyState title="Aucun site" text="Aucun site ne correspond aux filtres sélectionnés." />
      ) : (
        <Card>
          <Table>
            <Thead>
              <tr>
                <Th>Site</Th>
                <Th>Statut</Th>
                <Th>Score</Th>
                <Th className="text-right">Action</Th>
              </tr>
            </Thead>
            <Tbody>
              {filtered.map((s) => {
                const cfg = STATUS_CFG[s.status] || STATUS_CFG.warn;
                const Icon = cfg.icon;
                return (
                  <Tr
                    key={s.site_id}
                    className="cursor-pointer hover:bg-gray-50"
                    onClick={() => navigate(`/sites/${s.site_id}`)}
                  >
                    <Td>
                      <div>
                        <p className="text-sm font-medium text-gray-800">{s.nom}</p>
                        <p className="text-xs text-gray-400">ID {s.site_id}</p>
                      </div>
                    </Td>
                    <Td>
                      <div className="flex items-center gap-2">
                        <Icon size={16} className={cfg.color} />
                        <Badge status={cfg.badge}>{cfg.label}</Badge>
                      </div>
                    </Td>
                    <Td>
                      <div className="flex items-center gap-2">
                        <div className="w-20 bg-gray-200 rounded-full h-2">
                          <div
                            className={`h-2 rounded-full ${s.score >= 80 ? 'bg-green-500' : s.score >= 50 ? 'bg-amber-400' : 'bg-red-500'}`}
                            style={{ width: `${s.score}%` }}
                          />
                        </div>
                        <span className="text-xs font-bold text-gray-600">{s.score}%</span>
                      </div>
                    </Td>
                    <Td className="text-right">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/sites/${s.site_id}`);
                        }}
                      >
                        Résoudre
                      </Button>
                    </Td>
                  </Tr>
                );
              })}
            </Tbody>
          </Table>
        </Card>
      )}
    </PageShell>
  );
}
