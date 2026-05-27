// Énergie P0b visual credibility (2026-05-27, brief C5) — support
// optionnel d'une icône lucide-react par onglet (props `tabs[].icon`).
// Rétro-compat : si pas d'icône, rendu identique à l'historique.
export default function TabBar({ active, onChange, tabs }) {
  return (
    <div className="flex border-b border-gray-200">
      {tabs.map((t) => {
        const Icon = t.icon;
        return (
          <button
            key={t.id}
            onClick={() => onChange(t.id)}
            className={`px-4 py-2.5 text-xs font-medium border-b-2 transition-colors inline-flex items-center gap-1.5 ${
              active === t.id
                ? 'text-blue-600 border-blue-600'
                : 'text-gray-500 border-transparent hover:text-gray-700'
            }`}
          >
            {Icon && <Icon size={13} aria-hidden="true" />}
            {t.label}
          </button>
        );
      })}
    </div>
  );
}
