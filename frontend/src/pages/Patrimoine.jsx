/**
 * PROMEOS - Patrimoine (/patrimoine)
 * Table multi-sites with search, filters, pagination, sort, click-to-detail.
 */
import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Building2, Search, RotateCcw } from 'lucide-react';
import { Card, Badge, Button, Input, Select, Pagination, EmptyState } from '../ui';
import { Table, Thead, Tbody, Th, Tr, Td } from '../ui';
import { mockSites } from '../mocks/sites';

const PAGE_SIZE = 25;

const USAGE_OPTIONS = [
  { value: '', label: 'Tous les usages' },
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
  { value: '', label: 'Tous les statuts' },
  { value: 'conforme', label: 'Conforme' },
  { value: 'non_conforme', label: 'Non conforme' },
  { value: 'a_risque', label: 'A risque' },
  { value: 'a_evaluer', label: 'A evaluer' },
];

const STATUT_BADGE = {
  conforme: { status: 'ok', label: 'Conforme' },
  non_conforme: { status: 'crit', label: 'Non conforme' },
  a_risque: { status: 'warn', label: 'A risque' },
  a_evaluer: { status: 'neutral', label: 'A evaluer' },
};

export default function Patrimoine() {
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [filterUsage, setFilterUsage] = useState('');
  const [filterStatut, setFilterStatut] = useState('');
  const [page, setPage] = useState(1);
  const [sortCol, setSortCol] = useState('');
  const [sortDir, setSortDir] = useState('');

  const filtered = useMemo(() => {
    let result = [...mockSites];

    if (search) {
      const q = search.toLowerCase();
      result = result.filter(s =>
        s.nom.toLowerCase().includes(q) ||
        s.ville.toLowerCase().includes(q) ||
        s.adresse.toLowerCase().includes(q)
      );
    }
    if (filterUsage) result = result.filter(s => s.usage === filterUsage);
    if (filterStatut) result = result.filter(s => s.statut_conformite === filterStatut);

    if (sortCol) {
      result.sort((a, b) => {
        const va = a[sortCol];
        const vb = b[sortCol];
        if (typeof va === 'number') return sortDir === 'asc' ? va - vb : vb - va;
        return sortDir === 'asc'
          ? String(va).localeCompare(String(vb))
          : String(vb).localeCompare(String(va));
      });
    }

    return result;
  }, [search, filterUsage, filterStatut, sortCol, sortDir]);

  const total = filtered.length;
  const pageData = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  function handleSort(col) {
    if (sortCol === col) {
      setSortDir(d => d === 'asc' ? 'desc' : d === 'desc' ? '' : 'asc');
      if (sortDir === 'desc') setSortCol('');
    } else {
      setSortCol(col);
      setSortDir('asc');
    }
    setPage(1);
  }

  function resetFilters() {
    setSearch('');
    setFilterUsage('');
    setFilterStatut('');
    setPage(1);
  }

  const hasFilters = search || filterUsage || filterStatut;

  return (
    <div className="px-6 py-6 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Patrimoine</h2>
          <p className="text-sm text-gray-500 mt-0.5">{mockSites.length} sites au total</p>
        </div>
        <Button onClick={() => navigate('/import')}>Importer des sites</Button>
      </div>

      {/* Filters */}
      <Card className="p-4">
        <div className="flex items-end gap-3">
          <div className="flex-1 relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Rechercher par nom, ville, adresse..."
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              className="w-full pl-9 pr-4 py-2 border border-gray-300 rounded-lg text-sm
                placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <Select
            options={USAGE_OPTIONS}
            value={filterUsage}
            onChange={(e) => { setFilterUsage(e.target.value); setPage(1); }}
          />
          <Select
            options={STATUT_OPTIONS}
            value={filterStatut}
            onChange={(e) => { setFilterStatut(e.target.value); setPage(1); }}
          />
          {hasFilters && (
            <Button variant="ghost" size="sm" onClick={resetFilters}>
              <RotateCcw size={14} /> Reset
            </Button>
          )}
        </div>
      </Card>

      {/* Table */}
      {total === 0 ? (
        <EmptyState
          icon={Building2}
          title="Aucun site trouve"
          text="Modifiez vos filtres ou importez de nouveaux sites."
          ctaLabel="Reinitialiser les filtres"
          onCta={resetFilters}
        />
      ) : (
        <Card>
          <Table>
            <Thead>
              <tr>
                <Th sortable sorted={sortCol === 'nom' ? sortDir : ''} onSort={() => handleSort('nom')}>Site</Th>
                <Th sortable sorted={sortCol === 'ville' ? sortDir : ''} onSort={() => handleSort('ville')}>Ville</Th>
                <Th>Usage</Th>
                <Th>Conformite</Th>
                <Th sortable sorted={sortCol === 'risque_eur' ? sortDir : ''} onSort={() => handleSort('risque_eur')} className="text-right">Risque EUR</Th>
                <Th sortable sorted={sortCol === 'surface_m2' ? sortDir : ''} onSort={() => handleSort('surface_m2')} className="text-right">Surface</Th>
                <Th sortable sorted={sortCol === 'anomalies_count' ? sortDir : ''} onSort={() => handleSort('anomalies_count')} className="text-right">Anomalies</Th>
              </tr>
            </Thead>
            <Tbody>
              {pageData.map((site) => {
                const badge = STATUT_BADGE[site.statut_conformite] || STATUT_BADGE.a_evaluer;
                return (
                  <Tr key={site.id} onClick={() => navigate(`/sites/${site.id}`)}>
                    <Td className="font-medium text-gray-900">{site.nom}</Td>
                    <Td>{site.ville}</Td>
                    <Td><span className="capitalize text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded">{site.usage}</span></Td>
                    <Td><Badge status={badge.status}>{badge.label}</Badge></Td>
                    <Td className="text-right font-medium text-red-600">{site.risque_eur > 0 ? `${site.risque_eur.toLocaleString()} EUR` : '-'}</Td>
                    <Td className="text-right">{site.surface_m2.toLocaleString()} m2</Td>
                    <Td className="text-right">
                      {site.anomalies_count > 0 ? (
                        <span className={`font-medium ${site.anomalies_count > 4 ? 'text-red-600' : 'text-amber-600'}`}>{site.anomalies_count}</span>
                      ) : (
                        <span className="text-gray-400">0</span>
                      )}
                    </Td>
                  </Tr>
                );
              })}
            </Tbody>
          </Table>
          <Pagination page={page} pageSize={PAGE_SIZE} total={total} onChange={setPage} />
        </Card>
      )}
    </div>
  );
}
