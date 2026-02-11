export default function Skeleton({ className = '', rows = 1 }) {
  return (
    <div className="animate-pulse space-y-3">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className={`bg-gray-200 rounded h-4 ${className}`} />
      ))}
    </div>
  );
}

export function SkeletonCard() {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5 animate-pulse">
      <div className="h-3 bg-gray-200 rounded w-1/3 mb-3" />
      <div className="h-6 bg-gray-200 rounded w-1/2" />
    </div>
  );
}

export function SkeletonTable({ rows = 5, cols = 4 }) {
  return (
    <div className="animate-pulse">
      <div className="bg-gray-50 border-b px-4 py-3 flex gap-4">
        {Array.from({ length: cols }).map((_, i) => (
          <div key={i} className="h-3 bg-gray-200 rounded flex-1" />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="px-4 py-3 flex gap-4 border-b border-gray-50">
          {Array.from({ length: cols }).map((_, c) => (
            <div key={c} className="h-3 bg-gray-100 rounded flex-1" />
          ))}
        </div>
      ))}
    </div>
  );
}
