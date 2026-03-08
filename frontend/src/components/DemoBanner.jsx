import React, { useState } from 'react';
import { useDemo } from '../contexts/DemoContext';
import { useScope } from '../contexts/ScopeContext';
import { useExpertMode } from '../contexts/ExpertModeContext';
import { Sparkles, ArrowRight, CheckCircle, RefreshCw, Loader2, ChevronDown } from 'lucide-react';
import { seedDemoPack, clearApiCache } from '../services/api';

const DemoBanner = ({ onUpgradeClick }) => {
  const { demoEnabled, toggleDemo } = useDemo();
  const { org, sitesCount, portefeuilles, applyDemoScope } = useScope();
  const { isExpert } = useExpertMode();
  const [reloading, setReloading] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const handleReloadHelios = async () => {
    setReloading(true);
    try {
      const result = await seedDemoPack('helios', 'S', true);
      clearApiCache();
      if (result?.org_id) {
        applyDemoScope({
          orgId: result.org_id,
          orgNom: result.org_nom,
          defaultSiteId: result.default_site_id,
          defaultSiteName: result.default_site_name,
        });
      }
    } catch {
      // Banner is not critical — errors are surfaced in ImportPage
    }
    setReloading(false);
  };

  // Si onboarding réel fait et démo désactivée → bandeau vert avec nom org
  if (!demoEnabled && org?.nom && sitesCount > 0) {
    return (
      <div className="bg-gradient-to-r from-emerald-500 to-teal-500 text-white px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <CheckCircle size={20} />
          <span className="font-medium text-sm">
            {org.nom} — {sitesCount} site{sitesCount > 1 ? 's' : ''}, {portefeuilles.length}{' '}
            portefeuille{portefeuilles.length > 1 ? 's' : ''}
          </span>
        </div>
      </div>
    );
  }

  if (!demoEnabled) return null;

  // Mode discret : petit badge cliquable au lieu d'une bannière intrusive
  return (
    <div className="bg-slate-50 border-b border-slate-200/70 px-6 py-1.5 flex items-center justify-between">
      <button
        onClick={() => setExpanded((prev) => !prev)}
        className="flex items-center gap-2 text-xs text-slate-500 hover:text-slate-700 transition"
      >
        <Sparkles size={12} className="text-amber-500" />
        <span className="font-medium">Environnement de démonstration</span>
        {org?.nom && (
          <span className="text-slate-400">
            — {org.nom}, {sitesCount} site{sitesCount !== 1 ? 's' : ''}
          </span>
        )}
        <ChevronDown size={12} className={`transition ${expanded ? 'rotate-180' : ''}`} />
      </button>

      {/* Actions visibles uniquement quand expanded */}
      {expanded && (
        <div className="flex items-center gap-3">
          {isExpert && (
            <button
              onClick={handleReloadHelios}
              disabled={reloading}
              className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-700 px-2 py-1 rounded hover:bg-slate-100 transition disabled:opacity-50"
            >
              {reloading ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}
              {reloading ? 'Chargement...' : 'Recharger les données'}
            </button>
          )}
          <button
            onClick={toggleDemo}
            className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-700 px-2 py-1 rounded hover:bg-slate-100 transition"
          >
            <div className="relative w-7 h-3.5 bg-amber-300/60 rounded-full">
              <div className="absolute top-0.5 w-2.5 h-2.5 rounded-full bg-amber-500 transition-transform translate-x-3.5" />
            </div>
            Démo
          </button>
          <button
            onClick={onUpgradeClick}
            className="text-xs font-medium text-blue-600 hover:text-blue-700 px-2 py-1 rounded hover:bg-blue-50 transition flex items-center gap-1"
          >
            Connecter mes données réelles
            <ArrowRight size={12} />
          </button>
        </div>
      )}
    </div>
  );
};

export default DemoBanner;
