const styles = {
  ok:       'bg-green-100 text-green-800',
  warn:     'bg-amber-100 text-amber-800',
  crit:     'bg-red-100 text-red-800',
  info:     'bg-blue-100 text-blue-800',
  neutral:  'bg-gray-100 text-gray-700',
};

export default function Badge({ status = 'neutral', children, className = '' }) {
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${styles[status] || styles.neutral} ${className}`}>
      {children}
    </span>
  );
}
