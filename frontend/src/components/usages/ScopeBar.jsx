import { useScope } from '../../contexts/ScopeContext';

const LEVELS = [
  { id: 'org', label: 'Organisation' },
  { id: 'portfolio', label: 'Portefeuille' },
  { id: 'site', label: 'Site' },
];

export default function ScopeBar({ scopeLevel, onLevelChange }) {
  const { scopedSites, portefeuilles, scope, setSite, setPortefeuille, resetScope } = useScope();

  const handleLevelChange = (level) => {
    onLevelChange(level);
    if (level === 'org') {
      resetScope();
    } else if (level === 'portfolio') {
      if (portefeuilles?.[0]) setPortefeuille(portefeuilles[0].id);
    } else if (level === 'site') {
      if (scopedSites?.length > 0) setSite(scopedSites[0].id);
    }
  };

  const handleEntityChange = (value) => {
    if (scopeLevel === 'site') setSite(Number(value));
    else if (scopeLevel === 'portfolio') setPortefeuille(Number(value));
  };

  const options =
    scopeLevel === 'site'
      ? scopedSites?.map((s) => ({ value: s.id, label: s.nom })) || []
      : scopeLevel === 'portfolio'
        ? portefeuilles?.map((p) => ({ value: p.id, label: p.nom })) || []
        : [];

  return (
    <div className="px-7 py-3 flex items-center gap-2 border-b border-gray-200 bg-white">
      <span className="text-[10px] text-gray-400 font-semibold tracking-wide mr-1">PÉRIMÈTRE</span>
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
            value={scope.siteId || scope.portefeuilleId || ''}
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
  );
}
