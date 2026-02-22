/**
 * PROMEOS - Scope Switcher
 * Dropdown selectors: Org → Portefeuille → Site, plus a "scope pill" showing current scope.
 */
import { useState, useRef, useEffect } from 'react';
import { Building2, ChevronDown, X, Briefcase, MapPin } from 'lucide-react';
import { useScope } from '../contexts/ScopeContext';

export default function ScopeSwitcher() {
  const {
    scope, org, portefeuille, portefeuilles, orgs, orgSites, scopeLabel, sitesLoading,
    setOrg, setPortefeuille, setSite, resetScope,
  } = useScope();
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    function handleClick(e) { if (ref.current && !ref.current.contains(e.target)) setOpen(false); }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const hasSites = orgSites.length > 0;

  return (
    <div className="flex items-center gap-2" ref={ref}>
      {/* Scope pill */}
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 px-3 py-1.5 bg-blue-50 border border-blue-200 rounded-full text-sm text-blue-700 hover:bg-blue-100 transition"
      >
        <Building2 size={14} />
        <span className="font-medium">{org?.nom || 'Aucune org'}</span>
        {portefeuille && (
          <>
            <span className="text-blue-300">/</span>
            <span>{portefeuille.nom}</span>
          </>
        )}
        <span className="text-blue-400 text-xs">{sitesLoading ? 'Chargement\u2026' : scopeLabel}</span>
        <ChevronDown size={14} className={`transition ${open ? 'rotate-180' : ''}`} />
      </button>

      {/* Clear scope */}
      {(scope.portefeuilleId || scope.siteId) && (
        <button
          onClick={resetScope}
          className="p-1 rounded-full hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition"
          title="Réinitialiser le scope"
        >
          <X size={14} />
        </button>
      )}

      {/* Dropdown */}
      {open && (
        <div className="absolute top-full left-0 mt-1 w-72 bg-white rounded-lg shadow-lg border border-gray-200 z-50 py-2 max-h-[80vh] overflow-y-auto">
          {/* Org selector */}
          <div className="px-3 py-1.5">
            <p className="text-xs font-semibold text-gray-400 uppercase mb-1">Organisation</p>
            {orgs.map((o) => (
              <button
                key={o.id}
                onClick={() => { setOrg(o.id); }}
                className={`w-full text-left px-3 py-2 rounded text-sm transition flex items-center gap-2
                  ${o.id === scope.orgId ? 'bg-blue-50 text-blue-700 font-medium' : 'hover:bg-gray-50 text-gray-700'}`}
              >
                <Building2 size={14} />
                {o.nom}
              </button>
            ))}
          </div>

          <div className="border-t border-gray-100 my-1" />

          {/* Portefeuille selector */}
          <div className="px-3 py-1.5">
            <p className="text-xs font-semibold text-gray-400 uppercase mb-1">Portefeuille</p>
            <button
              onClick={() => { setPortefeuille(null); setOpen(false); }}
              className={`w-full text-left px-3 py-2 rounded text-sm transition flex items-center gap-2
                ${!scope.portefeuilleId ? 'bg-blue-50 text-blue-700 font-medium' : 'hover:bg-gray-50 text-gray-700'}`}
            >
              <Briefcase size={14} />
              Tous les portefeuilles
            </button>
            {portefeuilles.map((pf) => (
              <button
                key={pf.id}
                onClick={() => { setPortefeuille(pf.id); setOpen(false); }}
                className={`w-full text-left px-3 py-2 rounded text-sm transition flex items-center gap-2
                  ${pf.id === scope.portefeuilleId ? 'bg-blue-50 text-blue-700 font-medium' : 'hover:bg-gray-50 text-gray-700'}`}
              >
                <Briefcase size={14} />
                {pf.nom}
              </button>
            ))}
          </div>

          {/* Site selector — only shown when sites are available */}
          {hasSites && (
            <>
              <div className="border-t border-gray-100 my-1" />
              <div className="px-3 py-1.5">
                <p className="text-xs font-semibold text-gray-400 uppercase mb-1">
                  Site ({orgSites.length})
                </p>
                <button
                  onClick={() => { setSite(null); setOpen(false); }}
                  className={`w-full text-left px-3 py-2 rounded text-sm transition flex items-center gap-2
                    ${!scope.siteId ? 'bg-blue-50 text-blue-700 font-medium' : 'hover:bg-gray-50 text-gray-700'}`}
                >
                  <MapPin size={14} />
                  Tous les sites
                </button>
                {orgSites.map((site) => (
                  <button
                    key={site.id}
                    onClick={() => { setSite(site.id); setOpen(false); }}
                    className={`w-full text-left px-3 py-2 rounded text-sm transition flex items-center gap-2
                      ${site.id === scope.siteId ? 'bg-blue-50 text-blue-700 font-medium' : 'hover:bg-gray-50 text-gray-700'}`}
                  >
                    <MapPin size={14} />
                    <span className="truncate">{site.nom}</span>
                  </button>
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
