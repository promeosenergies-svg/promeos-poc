/**
 * PROMEOS — MeterSourceBadge (Step 25)
 * Badge indiquant la source d'un compteur unifié.
 * "EMS" (vert) = Meter avec données temps réel
 * "Import" (bleu) = Compteur legacy, données statiques
 */
import { Activity, Upload } from 'lucide-react';

const SOURCE_CONFIG = {
  meter: {
    label: 'EMS',
    icon: Activity,
    className: 'bg-green-50 text-green-700 ring-1 ring-green-200',
    tooltip: 'Compteur EMS — données temps réel',
  },
  compteur_legacy: {
    label: 'Import',
    icon: Upload,
    className: 'bg-blue-50 text-blue-700 ring-1 ring-blue-200',
    tooltip: 'Compteur legacy — données importées',
  },
};

export default function MeterSourceBadge({ source, className = '' }) {
  if (!source) return null;
  const cfg = SOURCE_CONFIG[source];
  if (!cfg) return null;
  const Icon = cfg.icon;
  return (
    <span
      className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium ${cfg.className} ${className}`}
      title={cfg.tooltip}
      data-testid="meter-source-badge"
    >
      <Icon size={10} />
      {cfg.label}
    </span>
  );
}
