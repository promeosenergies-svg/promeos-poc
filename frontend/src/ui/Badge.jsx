// Signal recipe aligned with SEVERITY_TINT: bg-{color}-50, text-{color}-700, border-{color}-200
const styles = {
  ok: 'bg-green-50 text-green-700 border border-green-200',
  warn: 'bg-amber-50 text-amber-700 border border-amber-200',
  crit: 'bg-red-50 text-red-700 border border-red-200',
  info: 'bg-blue-50 text-blue-700 border border-blue-200',
  neutral: 'bg-gray-50 text-gray-600 border border-gray-200',
};

export default function Badge({ status = 'neutral', children, className = '' }) {
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium whitespace-nowrap ${styles[status] || styles.neutral} ${className}`}
    >
      {children}
    </span>
  );
}
