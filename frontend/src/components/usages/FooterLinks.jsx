import { useNavigate } from 'react-router-dom';
import { toConsoDiag, toConformite, toUsages } from '../../services/routes';

const LINKS = [
  { label: '🔍 Diagnostic', to: '/diagnostic-conso' },
  { label: '📋 Conformité', to: '/conformite/tertiaire' },
  { label: '🧾 Factures', to: '/bill-intel' },
  { label: '🎯 Actions', to: '/actions' },
  { label: '🏢 Patrimoine', to: '/patrimoine' },
];

export default function FooterLinks() {
  const navigate = useNavigate();
  return (
    <div className="px-7 pb-6 grid grid-cols-2 lg:grid-cols-5 gap-2.5 print:hidden">
      {LINKS.map((l) => (
        <button
          key={l.to}
          onClick={() => navigate(l.to)}
          className="bg-white border border-gray-200 rounded-xl px-3.5 py-3 text-xs font-medium flex items-center justify-between hover:border-blue-400 hover:text-blue-600 transition-all hover:-translate-y-px"
        >
          {l.label} <span>→</span>
        </button>
      ))}
    </div>
  );
}
