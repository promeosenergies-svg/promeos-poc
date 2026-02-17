/**
 * PROMEOS — LayerToggle
 * Compact toggle panel for chart overlay layers.
 *
 * Props:
 *   layers   {object}  { talon: bool, meteo: bool, signature: bool, tunnel: bool, objectifs: bool }
 *   onToggle {fn}      (layerKey: string) => void
 */
import { Activity, Wind, TrendingUp, Target, Zap } from 'lucide-react';
import { LAYERS, LAYER_LABELS } from './types';

const LAYER_ICONS = {
  [LAYERS.TALON]: Zap,
  [LAYERS.METEO]: Wind,
  [LAYERS.SIGNATURE]: TrendingUp,
  [LAYERS.TUNNEL]: Activity,
  [LAYERS.OBJECTIFS]: Target,
};

const LAYER_ORDER = [LAYERS.TUNNEL, LAYERS.TALON, LAYERS.SIGNATURE, LAYERS.METEO, LAYERS.OBJECTIFS];

export default function LayerToggle({ layers = {}, onToggle }) {
  return (
    <div className="flex flex-col gap-1.5 min-w-[130px]">
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-0.5">Calques</p>
      {LAYER_ORDER.map(key => {
        const Icon = LAYER_ICONS[key] || Activity;
        const active = !!layers[key];
        return (
          <button
            key={key}
            onClick={() => onToggle(key)}
            className={`flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs font-medium border transition text-left ${
              active
                ? 'bg-blue-50 border-blue-200 text-blue-700'
                : 'bg-white border-gray-200 text-gray-500 hover:border-gray-300 hover:text-gray-700'
            }`}
          >
            <Icon size={12} className="shrink-0" />
            <span className="flex-1">{LAYER_LABELS[key]}</span>
            {/* Toggle indicator */}
            <span className={`w-2 h-2 rounded-full shrink-0 ${active ? 'bg-blue-500' : 'bg-gray-200'}`} />
          </button>
        );
      })}
    </div>
  );
}
