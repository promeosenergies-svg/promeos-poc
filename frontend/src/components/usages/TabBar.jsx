export default function TabBar({ active, onChange, tabs }) {
  return (
    <div className="flex border-b border-gray-200">
      {tabs.map((t) => (
        <button
          key={t.id}
          onClick={() => onChange(t.id)}
          className={`px-4 py-2.5 text-xs font-medium border-b-2 transition-colors ${
            active === t.id
              ? 'text-blue-600 border-blue-600'
              : 'text-gray-500 border-transparent hover:text-gray-700'
          }`}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}
