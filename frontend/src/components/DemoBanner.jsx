import React, { useState } from 'react';
import { useDemo } from '../contexts/DemoContext';
import { useScope } from '../contexts/ScopeContext';
import { Sparkles, ArrowRight, CheckCircle, ChevronDown } from 'lucide-react';
import { seedDemoPack } from '../services/api';

const DEMO_PACKS = [
  { value: 'helios', label: 'HELIOS (5 sites E2E)', size: 'S' },
  { value: 'casino', label: 'Casino (36 sites)', size: 'S' },
  { value: 'tertiaire', label: 'Tertiaire (10 sites)', size: 'S' },
];

const DemoBanner = ({ onUpgradeClick }) => {
  const { demoEnabled, toggleDemo } = useDemo();
  const { org, sitesCount, portefeuilles, applyDemoScope } = useScope();
  const [packLoading, setPackLoading] = useState(false);

  const handlePackChange = async (pack, size) => {
    setPackLoading(true);
    try {
      const result = await seedDemoPack(pack, size, true);
      if (result?.org_id) {
        applyDemoScope({
          orgId: result.org_id,
          orgNom: result.org_nom,
          defaultSiteId: result.default_site_id,
          defaultSiteName: result.default_site_name,
        });
      }
    } catch {
      // Silently fail — banner is not critical
    }
    setPackLoading(false);
  };

  // Si onboarding reel fait et demo desactivee → bandeau vert avec nom org
  if (!demoEnabled && org?.nom && sitesCount > 0) {
    return (
      <div className="bg-gradient-to-r from-emerald-500 to-teal-500 text-white px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <CheckCircle size={20} />
          <span className="font-medium text-sm">
            {org.nom} — {sitesCount} site{sitesCount > 1 ? 's' : ''}, {portefeuilles.length} portefeuille{portefeuilles.length > 1 ? 's' : ''}
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
          Mode Demo actif — Donnees de demonstration
          {org?.nom ? ` (${org.nom}, ${sitesCount} sites)` : ''}
        </span>
      </div>
      <div className="flex items-center gap-4">
        {/* Demo Pack Selector */}
        <div className="relative">
          <select
            disabled={packLoading}
            onChange={(e) => {
              const p = DEMO_PACKS.find(d => d.value === e.target.value);
              if (p) handlePackChange(p.value, p.size);
            }}
            defaultValue=""
            className="appearance-none bg-white/20 text-white text-xs px-3 py-1 pr-6 rounded cursor-pointer disabled:opacity-50"
          >
            <option value="" disabled>{packLoading ? 'Chargement...' : 'Changer de pack'}</option>
            {DEMO_PACKS.map(p => (
              <option key={p.value} value={p.value} className="text-gray-900">{p.label}</option>
            ))}
          </select>
          <ChevronDown size={12} className="absolute right-1.5 top-1/2 -translate-y-1/2 pointer-events-none" />
        </div>
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
