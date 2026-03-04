/**
 * PROMEOS Design System — Progress
 * Simple progress bar with optional label and color variants.
 */
const COLOR_MAP = {
  blue: 'bg-blue-500',
  green: 'bg-green-500',
  amber: 'bg-amber-500',
  red: 'bg-red-500',
  gray: 'bg-gray-400',
};

const SIZE_MAP = {
  sm: 'h-1.5',
  md: 'h-2.5',
  lg: 'h-4',
};

export default function Progress({
  value = 0,
  color = 'blue',
  size = 'md',
  label,
  className = '',
}) {
  const clamped = Math.max(0, Math.min(100, value));
  const barColor = COLOR_MAP[color] || COLOR_MAP.blue;
  const barSize = SIZE_MAP[size] || SIZE_MAP.md;

  return (
    <div className={className}>
      {label && (
        <div className="flex justify-between text-xs text-gray-500 mb-1">
          <span>{label}</span>
          <span>{Math.round(clamped)}%</span>
        </div>
      )}
      <div className={`w-full bg-gray-200 rounded-full overflow-hidden ${barSize}`}>
        <div
          className={`${barColor} ${barSize} rounded-full transition-all duration-500`}
          style={{ width: `${clamped}%` }}
        />
      </div>
    </div>
  );
}
