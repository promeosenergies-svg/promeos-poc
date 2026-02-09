import React from 'react';
import { useDemo } from '../contexts/DemoContext';
import { Sparkles, ArrowRight } from 'lucide-react';

const DemoBanner = ({ onUpgradeClick }) => {
  const { demoEnabled, toggleDemo } = useDemo();

  if (!demoEnabled) return null;

  return (
    <div className="bg-gradient-to-r from-amber-500 to-orange-500 text-white px-6 py-3 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <Sparkles size={20} />
        <span className="font-medium text-sm">
          Mode Demo actif — Donnees de demonstration (Groupe Casino, 120 sites)
        </span>
      </div>
      <div className="flex items-center gap-4">
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
