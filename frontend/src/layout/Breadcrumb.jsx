import { Link, useLocation } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';

const LABELS = {
  '': 'Command Center',
  'patrimoine': 'Patrimoine',
  'sites': 'Site',
  'conformite': 'Conformite',
  'compliance': 'Conformite',
  'cockpit': 'Cockpit Executif',
  'cockpit-2min': '2 Minutes',
  'action-plan': 'Plan d\'action',
  'consommations': 'Conso & Usages',
  'diagnostic-conso': 'Diagnostic Conso',
  'monitoring': 'Monitoring',
  'connectors': 'Connecteurs',
  'watchers': 'Veille Reglementaire',
  'segmentation': 'Segmentation',
  'import': 'Import',
  'status': 'Statut',
  'factures': 'Factures',
};

export default function Breadcrumb() {
  const { pathname } = useLocation();
  const parts = pathname.split('/').filter(Boolean);

  const crumbs = [{ label: 'PROMEOS', to: '/' }];
  let path = '';
  for (const part of parts) {
    path += '/' + part;
    crumbs.push({ label: LABELS[part] || part, to: path });
  }

  return (
    <nav className="flex items-center gap-1 text-sm text-gray-500">
      {crumbs.map((c, i) => (
        <span key={c.to} className="flex items-center gap-1">
          {i > 0 && <ChevronRight size={14} className="text-gray-300" />}
          {i < crumbs.length - 1 ? (
            <Link to={c.to} className="hover:text-gray-700 transition">{c.label}</Link>
          ) : (
            <span className="text-gray-800 font-medium">{c.label}</span>
          )}
        </span>
      ))}
    </nav>
  );
}
