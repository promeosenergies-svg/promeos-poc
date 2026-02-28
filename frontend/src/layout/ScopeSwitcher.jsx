/**
 * PROMEOS - Scope Switcher
 * Dropdown selectors: Org → Portefeuille → Site, plus a "scope pill" showing current scope.
 *
 * Dropdown rendered via createPortal (document.body, position:fixed, z-[120])
 * to escape the header's backdrop-blur-md stacking context.
 */
import { useState, useRef, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { Building2, ChevronDown, X, Briefcase, MapPin } from 'lucide-react';
import { useScope } from '../contexts/ScopeContext';

export default function ScopeSwitcher() {
  const {
    scope, org, portefeuille, portefeuilles, orgs, orgSites, scopeLabel, sitesLoading,
    setOrg, setPortefeuille, setSite, resetScope,
  } = useScope();
  const [open, setOpen] = useState(false);
  const [dropCoords, setDropCoords] = useState(null);
  const triggerRef = useRef(null);
  const dropRef    = useRef(null);

  // Close on outside click — checks both the trigger pill and the portal dropdown
  useEffect(() => {
    if (!open) return;
    function onClickOutside(e) {
      if (triggerRef.current?.contains(e.target)) return;
      if (dropRef.current?.contains(e.target)) return;
      setOpen(false);
    }
    document.addEventListener('mousedown', onClickOutside);
    return () => document.removeEventListener('mousedown', onClickOutside);
  }, [open]);

  const toggleOpen = useCallback(() => {
    if (!open && triggerRef.current) {
      const rect = triggerRef.current.getBoundingClientRect();
      setDropCoords({ top: rect.bottom + 4, left: rect.left });
    }
    setOpen((prev) => !prev);
  }, [open]);

  const hasSites = orgSites.length > 0;

  return (
    <div className="flex items-center gap-2">
      {/* Scope pill trigger */}
      <button
        ref={triggerRef}
        onClick={toggleOpen}
        aria-haspopup="listbox"
        aria-expanded={open}
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

      {/* Dropdown — portal to document.body, position:fixed, z-[120] */}
      {open && dropCoords && createPortal(
        <div
          ref={dropRef}
          role="listbox"
          className="fixed w-72 bg-white rounded-lg shadow-xl border border-gray-200 py-2 max-h-[80vh] overflow-y-auto z-[120]"
          style={{ top: dropCoords.top, left: dropCoords.left }}
        >
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
        </div>,
        document.body,
      )}
    </div>
  );
}
