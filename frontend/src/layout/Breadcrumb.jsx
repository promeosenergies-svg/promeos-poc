import { Link, useLocation } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';

const LABELS = {
  '': 'Accueil',
  'patrimoine': 'Patrimoine',
  'sites': 'Site',
  'conformite': 'Conformit\u00e9',
  'compliance': 'Conformit\u00e9',
  'cockpit': 'Vue Ex\u00e9cutive',
  'cockpit-2min': '2 Minutes',
  'actions': "Plan d'action",
  'action-plan': "Plan d'action",
  'consommations': 'Consommation',
  'diagnostic-conso': 'Anomalies',
  'bill-intel': 'Factures & \u00e9carts',
  'achat-energie': 'Achat \u00c9nergie',
  'monitoring': 'Performance & suivi',
  'connectors': 'Connecter des sources',
  'watchers': 'Veille r\u00e9glementaire',
  'segmentation': 'Segmentation',
  'import': 'Importer des fichiers',
  'kb': 'R\u00e8gles & r\u00e9f\u00e9rentiels',
  'status': 'Statut',
  'factures': 'Factures',
  'plan-action': "Plan d'action",
  'anomalies': 'Anomalies',
  'performance': 'Performance & suivi',
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
