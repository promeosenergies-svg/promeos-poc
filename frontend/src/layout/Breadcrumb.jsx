import { Link, useLocation } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';

const LABELS = {
  '': 'Tableau de bord',
  'patrimoine': 'Patrimoine',
  'sites': 'Site',
  'conformite': 'Conformité',
  'compliance': 'Conformité',
  'cockpit': 'Vue exécutive',
  'cockpit-2min': 'Vue exécutive express',
  'actions': "Plan d'actions",
  'action-plan': "Plan d'actions",
  'consommations': 'Consommations',
  'diagnostic-conso': 'Diagnostic',
  'bill-intel': 'Facturation',
  'achat-energie': 'Achats énergie',
  'monitoring': 'Performance',
  'connectors': 'Connexions',
  'watchers': 'Veille',
  'segmentation': 'Segmentation',
  'import': 'Imports',
  'kb': 'Référentiels',
  'notifications': 'Alertes',
  'status': 'Statut',
  'login': 'Connexion',
  'admin': 'Administration',
  'users': 'Utilisateurs',
  // Aliases
  'factures': 'Facturation',
  'facturation': 'Facturation',
  'plan-action': "Plan d'actions",
  'plan-actions': "Plan d'actions",
  'anomalies': 'Diagnostic',
  'diagnostic': 'Diagnostic',
  'performance': 'Performance',
  'achats': 'Achats énergie',
  'purchase': 'Achats énergie',
  'achat-assistant': 'Assistant Achat',
  'referentiels': 'Référentiels',
  'synthese': 'Vue exécutive',
  'executive': 'Vue exécutive',
  'dashboard': 'Tableau de bord',
  'conso': 'Consommations',
  'imports': 'Imports',
  'connexions': 'Connexions',
  'veille': 'Veille',
  'alertes': 'Alertes',
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
