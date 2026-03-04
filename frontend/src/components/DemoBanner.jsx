import React, { useState } from 'react';
import { useDemo } from '../contexts/DemoContext';
import { useScope } from '../contexts/ScopeContext';
import { Sparkles, ArrowRight, CheckCircle, RefreshCw, Loader2 } from 'lucide-react';
import { seedDemoPack, clearApiCache } from '../services/api';

const DemoBanner = ({ onUpgradeClick }) => {
  const { demoEnabled, toggleDemo } = useDemo();
  const { org, sitesCount, portefeuilles, applyDemoScope } = useScope();
  const [reloading, setReloading] = useState(false);

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

  // Si onboarding reel fait et demo desactivee → bandeau vert avec nom org
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

  return (
    <div className="bg-gradient-to-r from-amber-500 to-orange-500 text-white px-6 py-3 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <Sparkles size={20} />
        <span className="font-medium text-sm">
          Mode Demo actif — Donnees HELIOS
          {org?.nom ? ` (${org.nom}, ${sitesCount} sites)` : ''}
        </span>
      </div>
      <div className="flex items-center gap-4">
        {/* Reload HELIOS */}
        <button
          onClick={handleReloadHelios}
          disabled={reloading}
          className="flex items-center gap-1.5 bg-white/20 text-white text-xs px-3 py-1.5 rounded hover:bg-white/30 transition disabled:opacity-50"
        >
          {reloading ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}
          {reloading ? 'Chargement...' : 'Recharger HELIOS'}
        </button>
        {/* Toggle */}
        <button
          onClick={toggleDemo}
          className="flex items-center gap-2 text-sm opacity-80 hover:opacity-100 transition"
        >
          <div className="relative w-10 h-5 bg-white/30 rounded-full">
            <div className="absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform translate-x-5" />
          </div>
          <span>Demo</span>
        </button>
        {/* Upgrade CTA */}
        <button
          onClick={onUpgradeClick}
          className="bg-white text-orange-600 px-4 py-1.5 rounded-lg text-sm font-semibold hover:bg-orange-50 transition flex items-center gap-1"
        >
          Connecter mes donnees reelles
          <ArrowRight size={14} />
        </button>
      </div>
    </div>
  );
};

export default DemoBanner;
