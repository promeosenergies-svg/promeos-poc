import { useEffect, useState, useMemo } from 'react';
import { useScope } from '../../contexts/ScopeContext';
import { getScopeTree, getArchetypesInScope } from '../../services/api';

const LEVELS = [
  { id: 'org', label: 'Organisation' },
  { id: 'entite', label: 'Entité juridique' },
  { id: 'portfolio', label: 'Portefeuille' },
  { id: 'site', label: 'Site' },
];

export default function ScopeBar({
  scopeLevel,
  onLevelChange,
  archetypeFilter,
  onArchetypeFilter,
}) {
  const { scopedSites, scope, setSite, setEntite, setPortefeuille, resetScope } = useScope();
  const [scopeTree, setScopeTree] = useState(null);
  const [archetypes, setArchetypes] = useState([]);

  // Fetch scope tree from API
  useEffect(() => {
    getScopeTree()
      .then(setScopeTree)
      .catch(() => {});
  }, [scope?.orgId]);

  // Fetch archetype distribution for current scope
  useEffect(() => {
    const params = {};
    if (scopeLevel === 'entite' && scope.entiteId) params.entityId = scope.entiteId;
    else if (scopeLevel === 'portfolio' && scope.portefeuilleId)
      params.portefeuilleId = scope.portefeuilleId;
    else if (scopeLevel === 'site' && scope.siteId) params.siteId = scope.siteId;
    getArchetypesInScope(params)
      .then((r) => setArchetypes(r?.archetypes || []))
      .catch(() => {});
  }, [scope?.orgId, scope.entiteId, scope.portefeuilleId, scope.siteId, scopeLevel]);

  // Derive dropdown options from scope tree
  const options = useMemo(() => {
    if (scopeLevel === 'site') {
      return scopedSites?.map((s) => ({ value: s.id, label: s.nom })) || [];
    }
    if (!scopeTree?.entites) return [];
    if (scopeLevel === 'entite') {
      return scopeTree.entites.map((ej) => {
        const siteCount = ej.portefeuilles.reduce((s, pf) => s + pf.sites.length, 0);
        return { value: ej.id, label: `${ej.nom} (${siteCount} site${siteCount > 1 ? 's' : ''})` };
      });
    }
    if (scopeLevel === 'portfolio') {
      const entite = scope.entiteId
        ? scopeTree.entites.find((ej) => ej.id === scope.entiteId)
        : null;
      const pfs = entite
        ? entite.portefeuilles
        : scopeTree.entites.flatMap((ej) => ej.portefeuilles);
      return pfs.map((pf) => ({
        value: pf.id,
        label: `${pf.nom} (${pf.sites.length} site${pf.sites.length > 1 ? 's' : ''})`,
      }));
    }
    return [];
  }, [scopeLevel, scopeTree, scopedSites, scope.entiteId]);

  const handleLevelChange = (level) => {
    onLevelChange(level);
    onArchetypeFilter?.(null);
    if (level === 'org') {
      resetScope();
    } else if (level === 'entite') {
      const firstEntite = scopeTree?.entites?.[0];
      if (firstEntite) setEntite(firstEntite.id);
      else resetScope();
    } else if (level === 'portfolio') {
      const pfs = scopeTree?.entites?.flatMap((ej) => ej.portefeuilles) || [];
      if (pfs[0]) setPortefeuille(pfs[0].id);
      else resetScope();
    } else if (level === 'site') {
      if (scopedSites?.length > 0) setSite(scopedSites[0].id);
    }
  };

  const handleEntityChange = (value) => {
    if (scopeLevel === 'entite') setEntite(Number(value));
    else if (scopeLevel === 'portfolio') setPortefeuille(Number(value));
    else if (scopeLevel === 'site') setSite(Number(value));
  };

  const currentValue =
    scopeLevel === 'entite'
      ? scope.entiteId || ''
      : scopeLevel === 'portfolio'
        ? scope.portefeuilleId || ''
        : scope.siteId || '';

  return (
    <div className="border-b border-gray-200 bg-white">
      <div className="px-7 py-3 flex items-center gap-2">
        <span className="text-[10px] text-gray-400 font-semibold tracking-wide mr-1">
          PÉRIMÈTRE
        </span>
        {LEVELS.map((l) => (
          <button
            key={l.id}
            onClick={() => handleLevelChange(l.id)}
            className={`px-3.5 py-1.5 rounded-full text-xs font-medium border transition-all ${
              scopeLevel === l.id
                ? 'bg-blue-600 text-white border-blue-600'
                : 'bg-white text-gray-600 border-gray-200 hover:border-blue-400 hover:text-blue-600'
            }`}
          >
            {l.label}
          </button>
        ))}
        {options.length > 0 && (
          <>
            <span className="text-gray-300 text-sm">›</span>
            <select
              className="px-2.5 py-1.5 rounded-lg border border-gray-200 text-xs font-medium bg-white cursor-pointer"
              value={currentValue}
              onChange={(e) => handleEntityChange(e.target.value)}
            >
              {options.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </>
        )}
        <span className="ml-auto text-[10px] text-gray-400">
          {scopedSites?.length || 0} site{(scopedSites?.length || 0) > 1 ? 's' : ''}
        </span>
      </div>
      {/* Archetype filter chips */}
      {archetypes.length > 1 && (
        <div className="px-7 pb-2.5 flex items-center gap-1.5">
          <span className="text-[10px] text-gray-400 font-semibold tracking-wide mr-1">FILTRE</span>
          <button
            onClick={() => onArchetypeFilter?.(null)}
            className={`px-2.5 py-1 rounded-full text-[11px] font-medium border transition-all ${
              !archetypeFilter
                ? 'bg-indigo-600 text-white border-indigo-600'
                : 'bg-white text-gray-500 border-gray-200 hover:border-indigo-400'
            }`}
          >
            Tous ({archetypes.reduce((s, a) => s + a.count, 0)})
          </button>
          {archetypes.map((a) => (
            <button
              key={a.code}
              onClick={() => onArchetypeFilter?.(archetypeFilter === a.code ? null : a.code)}
              className={`px-2.5 py-1 rounded-full text-[11px] font-medium border transition-all ${
                archetypeFilter === a.code
                  ? 'bg-indigo-600 text-white border-indigo-600'
                  : 'bg-white text-gray-500 border-gray-200 hover:border-indigo-400'
              }`}
            >
              {a.label} ({a.count})
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
