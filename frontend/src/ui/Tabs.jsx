import { tint } from './colorTokens';

const DEFAULT_TINT = { active: 'border-blue-600 text-blue-600', ring: 'ring-blue-500' };

export default function Tabs({ tabs, active, onChange, tint: tintOverride, moduleKey }) {
  const t = tintOverride || (moduleKey ? tint.module(moduleKey).tab() : DEFAULT_TINT);
  return (
    <div className="border-b border-gray-200">
      <nav className="flex gap-0 -mb-px">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => onChange(tab.id)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition
              focus-visible:outline-none focus-visible:ring-2 focus-visible:${t.ring}
              ${active === tab.id
                ? t.active
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
          >
            {tab.label}
          </button>
        ))}
      </nav>
    </div>
  );
}
