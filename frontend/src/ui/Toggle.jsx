/**
 * PROMEOS Design System — Toggle (Switch)
 * Simple toggle with label. Used for Expert Mode and density toggles.
 */
export default function Toggle({ checked, onChange, label, size = 'md', className = '' }) {
  const sizes = {
    sm: { track: 'w-8 h-4', thumb: 'w-3 h-3', translate: 'translate-x-4' },
    md: { track: 'w-10 h-5', thumb: 'w-4 h-4', translate: 'translate-x-5' },
  };
  const s = sizes[size] || sizes.md;

  return (
    <label className={`inline-flex items-center gap-2 cursor-pointer select-none ${className}`}>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`relative inline-flex shrink-0 ${s.track} items-center rounded-full transition-colors
          focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2
          ${checked ? 'bg-blue-600' : 'bg-gray-300'}`}
      >
        <span
          className={`inline-block ${s.thumb} rounded-full bg-white shadow transition-transform
            ${checked ? s.translate : 'translate-x-0.5'}`}
        />
      </button>
      {label && <span className="text-sm text-gray-600">{label}</span>}
    </label>
  );
}
