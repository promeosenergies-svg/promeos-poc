/**
 * PROMEOS - Scope Switcher
 * Dropdown selectors: Org → Portefeuille → Site, plus a "scope pill" showing current scope.
 *
 * Dropdown rendered via createPortal (document.body, position:fixed, z-[120])
 * to escape the header's backdrop-blur-md stacking context.
 *
 * Sprint Nav: search in site list, scope feedback, improved pill, tooltips.
 */
import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { createPortal } from 'react-dom';
import { Building2, ChevronDown, X, Briefcase, MapPin, Search, Check } from 'lucide-react';
import { useScope } from '../contexts/ScopeContext';
import useFloatingPortalPosition from '../hooks/useFloatingPortalPosition';

// Lightweight scope feedback — brief confirmation that auto-dismisses
function useScopeFeedback(duration = 2200) {
  const [msg, setMsg] = useState(null);
  const timer = useRef(null);
  const show = useCallback(
    (text) => {
      clearTimeout(timer.current);
      setMsg(text);
      timer.current = setTimeout(() => setMsg(null), duration);
    },
    [duration]
  );
  useEffect(() => () => clearTimeout(timer.current), []);
  return { msg, show };
}

export default function ScopeSwitcher() {
  const {
    scope,
    org,
    portefeuille,
    portefeuilles,
    orgs,
    orgSites,
    scopeLabel,
    sitesLoading,
    sitesCount,
    setOrg,
    setPortefeuille,
    setSite,
    resetScope,
  } = useScope();
  const [open, setOpen] = useState(false);
  const [siteSearch, setSiteSearch] = useState('');
  const searchRef = useRef(null);
  const triggerRef = useRef(null);
  const dropRef = useRef(null);
  const { msg: feedbackMsg, show: showFeedback } = useScopeFeedback();

  // Premium positioning: scroll/resize/zoom auto-reposition
  const { style: dropStyle } = useFloatingPortalPosition({
    isOpen: open,
    triggerRef,
    portalRef: dropRef,
  });

  // Close on outside click (cross-portal) + ESC
  useEffect(() => {
    if (!open) return;
    function onClickOutside(e) {
      if (triggerRef.current?.contains(e.target)) return;
      if (dropRef.current?.contains(e.target)) return;
      setOpen(false);
    }
    function onKeyDown(e) {
      if (e.key === 'Escape') setOpen(false);
    }
    document.addEventListener('mousedown', onClickOutside);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('mousedown', onClickOutside);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [open]);

  // Auto-focus search when dropdown opens + reset search
  useEffect(() => {
    if (open) {
      setSiteSearch('');
      // Small delay to let portal render before focusing
      const t = setTimeout(() => searchRef.current?.focus(), 60);
      return () => clearTimeout(t);
    }
  }, [open]);

  const toggleOpen = useCallback(() => setOpen((prev) => !prev), []);

  const hasSites = orgSites.length > 0;
  const showSearch = orgSites.length >= 6;

  // Filtered sites by search term
  const filteredSites = useMemo(() => {
    if (!siteSearch.trim()) return orgSites;
    const q = siteSearch.trim().toLowerCase();
    return orgSites.filter((s) => {
      const nom = (s.nom || '').toLowerCase();
      const ville = (s.ville || s.city || '').toLowerCase();
      const code = (s.code_postal || '').toLowerCase();
      return nom.includes(q) || ville.includes(q) || code.includes(q);
    });
  }, [orgSites, siteSearch]);

  // Site count per portefeuille (for counters)
  const pfSiteCounts = useMemo(() => {
    const counts = {};
    for (const s of orgSites) {
      const pfId = s.portefeuille_id ?? ((s.id - 1) % 5) + 1;
      counts[pfId] = (counts[pfId] || 0) + 1;
    }
    return counts;
  }, [orgSites]);

  // Scope change handlers with feedback
  const handleSetOrg = useCallback(
    (orgId) => {
      setOrg(orgId);
      const o = orgs.find((x) => x.id === orgId);
      showFeedback(`Societe : ${o?.nom || orgId}`);
    },
    [setOrg, orgs, showFeedback]
  );

  const handleSetPortefeuille = useCallback(
    (pfId) => {
      setPortefeuille(pfId);
      setOpen(false);
      if (pfId) {
        const pf = portefeuilles.find((p) => p.id === pfId);
        showFeedback(`Portefeuille : ${pf?.nom || pfId}`);
      } else {
        showFeedback('Tous les regroupements');
      }
    },
    [setPortefeuille, portefeuilles, showFeedback]
  );

  const handleSetSite = useCallback(
    (siteId) => {
      setSite(siteId);
      setOpen(false);
      if (siteId) {
        const s = orgSites.find((x) => x.id === siteId);
        showFeedback(`Site : ${s?.nom || siteId}`);
      } else {
        showFeedback('Tous les sites');
      }
    },
    [setSite, orgSites, showFeedback]
  );

  // Improved pill label — always show org + count context
  const pillSiteLabel = useMemo(() => {
    if (sitesLoading) return 'Chargement\u2026';
    if (scope.siteId) {
      const s = orgSites.find((x) => String(x.id) === String(scope.siteId));
      return s ? s.nom : scopeLabel;
    }
    return `${sitesCount} site${sitesCount !== 1 ? 's' : ''}`;
  }, [sitesLoading, scope.siteId, orgSites, scopeLabel, sitesCount]);

  return (
    <div className="flex items-center gap-2">
      {/* Scope pill trigger — always shows org + scope context */}
      <button
        ref={triggerRef}
        onClick={toggleOpen}
        aria-haspopup="listbox"
        aria-expanded={open}
        data-testid="scope-switcher-trigger"
        className="flex items-center gap-2 px-3 py-1.5 bg-blue-50 border border-blue-200 rounded-full text-sm text-blue-700 hover:bg-blue-100 transition max-w-[360px]"
      >
        <Building2 size={14} className="shrink-0" />
        <span className="font-medium truncate">{org?.nom || 'Aucune org'}</span>
        {portefeuille && (
          <>
            <span className="text-blue-300 shrink-0">/</span>
            <span className="truncate">{portefeuille.nom}</span>
          </>
        )}
        <span className="text-blue-400 text-xs whitespace-nowrap shrink-0">
          {scope.siteId ? '\u00b7' : '\u2014'} {pillSiteLabel}
        </span>
        <ChevronDown size={14} className={`shrink-0 transition ${open ? 'rotate-180' : ''}`} />
      </button>

      {/* Clear scope */}
      {(scope.portefeuilleId || scope.siteId) && (
        <button
          onClick={() => {
            resetScope();
            showFeedback('Scope réinitialisé');
          }}
          className="p-1 rounded-full hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition"
          title="Réinitialiser le scope"
        >
          <X size={14} />
        </button>
      )}

      {/* Scope feedback toast — brief inline confirmation */}
      {feedbackMsg && (
        <div
          className="flex items-center gap-1.5 px-2.5 py-1 bg-green-50 border border-green-200 rounded-full text-xs text-green-700 font-medium animate-[fadeIn_0.2s_ease-out]"
          data-testid="scope-feedback"
        >
          <Check size={12} className="shrink-0" />
          <span className="truncate max-w-[200px]">{feedbackMsg}</span>
        </div>
      )}

      {/* Dropdown — portal to document.body, position:fixed, z-[120], auto-repositions on scroll/resize */}
      {open &&
        createPortal(
          <div
            ref={dropRef}
            role="listbox"
            data-testid="scope-switcher-panel"
            className="fixed w-80 bg-white rounded-lg shadow-xl border border-gray-200 py-2 max-h-[80vh] overflow-y-auto z-[120]"
            style={dropStyle}
          >
            {/* Org selector */}
            <div className="px-3 py-1.5">
              <p className="text-xs font-semibold text-gray-400 uppercase mb-1">Societe</p>
              {orgs.map((o) => (
                <button
                  key={o.id}
                  onClick={() => handleSetOrg(o.id)}
                  className={`w-full text-left px-3 py-2 rounded text-sm transition flex items-center gap-2
                  ${o.id === scope.orgId ? 'bg-blue-50 text-blue-700 font-medium' : 'hover:bg-gray-50 text-gray-700'}`}
                >
                  <Building2 size={14} className="shrink-0" />
                  <span className="truncate">{o.nom}</span>
                </button>
              ))}
            </div>

            <div className="border-t border-gray-100 my-1" />

            {/* Portefeuille selector */}
            <div className="px-3 py-1.5">
              <p className="text-xs font-semibold text-gray-400 uppercase mb-1">Regroupement</p>
              <button
                onClick={() => handleSetPortefeuille(null)}
                className={`w-full text-left px-3 py-2 rounded text-sm transition flex items-center gap-2
                ${!scope.portefeuilleId ? 'bg-blue-50 text-blue-700 font-medium' : 'hover:bg-gray-50 text-gray-700'}`}
              >
                <Briefcase size={14} className="shrink-0" />
                Tous les regroupements
              </button>
              {portefeuilles.map((pf) => (
                <button
                  key={pf.id}
                  onClick={() => handleSetPortefeuille(pf.id)}
                  className={`w-full text-left px-3 py-2 rounded text-sm transition flex items-center justify-between gap-2
                  ${pf.id === scope.portefeuilleId ? 'bg-blue-50 text-blue-700 font-medium' : 'hover:bg-gray-50 text-gray-700'}`}
                >
                  <span className="flex items-center gap-2 min-w-0">
                    <Briefcase size={14} className="shrink-0" />
                    <span className="truncate" title={pf.nom}>
                      {pf.nom}
                    </span>
                  </span>
                  {pfSiteCounts[pf.id] > 0 && (
                    <span className="text-[10px] text-gray-400 shrink-0">
                      {pfSiteCounts[pf.id]} site{pfSiteCounts[pf.id] > 1 ? 's' : ''}
                    </span>
                  )}
                </button>
              ))}
            </div>

            {/* Site selector — with search when 6+ sites */}
            {hasSites && (
              <>
                <div className="border-t border-gray-100 my-1" />
                <div className="px-3 py-1.5">
                  <p className="text-xs font-semibold text-gray-400 uppercase mb-1">
                    Site ({orgSites.length})
                  </p>

                  {/* Search input */}
                  {showSearch && (
                    <div className="relative mb-2">
                      <Search
                        size={14}
                        className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400"
                      />
                      <input
                        ref={searchRef}
                        type="text"
                        value={siteSearch}
                        onChange={(e) => setSiteSearch(e.target.value)}
                        placeholder="Rechercher un site…"
                        data-testid="scope-site-search"
                        className="w-full pl-8 pr-3 py-1.5 border border-gray-200 rounded-lg text-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                      />
                    </div>
                  )}

                  <button
                    onClick={() => handleSetSite(null)}
                    className={`w-full text-left px-3 py-2 rounded text-sm transition flex items-center gap-2
                    ${!scope.siteId ? 'bg-blue-50 text-blue-700 font-medium' : 'hover:bg-gray-50 text-gray-700'}`}
                  >
                    <MapPin size={14} className="shrink-0" />
                    Tous les sites
                  </button>
                  {filteredSites.map((site) => (
                    <button
                      key={site.id}
                      onClick={() => handleSetSite(site.id)}
                      className={`w-full text-left px-3 py-2 rounded text-sm transition flex items-center gap-2
                      ${site.id === scope.siteId ? 'bg-blue-50 text-blue-700 font-medium' : 'hover:bg-gray-50 text-gray-700'}`}
                    >
                      <MapPin size={14} className="shrink-0" />
                      <span className="truncate" title={site.nom}>
                        {site.nom}
                      </span>
                      {site.ville && (
                        <span className="text-[10px] text-gray-400 shrink-0 ml-auto">
                          {site.ville}
                        </span>
                      )}
                    </button>
                  ))}
                  {/* Empty state */}
                  {showSearch && siteSearch.trim() && filteredSites.length === 0 && (
                    <p
                      className="text-xs text-gray-400 text-center py-3"
                      data-testid="scope-site-empty"
                    >
                      Aucun site ne correspond à &laquo;{'\u00a0'}
                      {siteSearch.trim()}
                      {'\u00a0'}&raquo;
                    </p>
                  )}
                </div>
              </>
            )}
          </div>,
          document.body
        )}
    </div>
  );
}
