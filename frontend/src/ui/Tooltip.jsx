/**
 * PROMEOS Design System — Tooltip
 * CSS-only hover tooltip. No JS positioning needed for a POC.
 */
export default function Tooltip({ text, children, position = 'top', className = '' }) {
  // Guard: no text → render children as-is, no invisible tooltip bubble
  if (!text) return <span className={`inline-flex ${className}`}>{children}</span>;

  const posClass = {
    top: 'bottom-full left-1/2 -translate-x-1/2 mb-2',
    bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
    left: 'right-full top-1/2 -translate-y-1/2 mr-2',
    right: 'left-full top-1/2 -translate-y-1/2 ml-2',
  };

  return (
    <span className={`relative inline-flex group ${className}`}>
      {children}
      <span
        className={`absolute ${posClass[position] || posClass.top} z-50
          px-2 py-1 text-xs text-white bg-gray-900 rounded shadow-lg whitespace-nowrap
          opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity duration-150`}
        role="tooltip"
      >
        {text}
      </span>
    </span>
  );
}
