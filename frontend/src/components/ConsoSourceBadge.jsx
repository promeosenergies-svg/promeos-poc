/**
 * PROMEOS — A.1 ConsoSourceBadge
 * Badge discret indiquant la source de la consommation affichee.
 * "Compteur" (vert), "Facture" (bleu), "Estime" (orange).
 */
import { Activity, FileText, HelpCircle } from 'lucide-react';

const SOURCE_CONFIG = {
  metered: {
    label: 'Compteur',
    icon: Activity,
    className: 'bg-green-50 text-green-700 ring-1 ring-green-200',
    tooltip: 'Données issues des relevés compteur (source primaire)',
  },
  billed: {
    label: 'Facture',
    icon: FileText,
    className: 'bg-blue-50 text-blue-700 ring-1 ring-blue-200',
    tooltip: 'Données issues des factures fournisseur',
  },
  estimated: {
    label: 'Estimé',
    icon: HelpCircle,
    className: 'bg-amber-50 text-amber-700 ring-1 ring-amber-200',
    tooltip: 'Estimation basée sur la consommation annuelle déclarée',
  },
};

export default function ConsoSourceBadge({ source, className = '' }) {
  if (!source) return null;
  const cfg = SOURCE_CONFIG[source];
  if (!cfg) return null;
  const Icon = cfg.icon;
  return (
    <span
      className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium ${cfg.className} ${className}`}
      title={cfg.tooltip}
      data-testid="conso-source-badge"
    >
      <Icon size={10} />
      {cfg.label}
    </span>
  );
}
