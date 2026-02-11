export function Table({ children, className = '' }) {
  return (
    <div className={`overflow-x-auto ${className}`}>
      <table className="w-full text-sm">{children}</table>
    </div>
  );
}

export function Thead({ children }) {
  return <thead className="bg-gray-50 border-b border-gray-200">{children}</thead>;
}

export function Th({ children, className = '', sortable, sorted, onSort }) {
  const base = 'px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider';
  if (!sortable) return <th className={`${base} ${className}`}>{children}</th>;
  return (
    <th className={`${base} cursor-pointer select-none hover:text-gray-700 ${className}`} onClick={onSort}>
      <span className="inline-flex items-center gap-1">
        {children}
        {sorted === 'asc' && <span>&#9650;</span>}
        {sorted === 'desc' && <span>&#9660;</span>}
        {!sorted && <span className="text-gray-300">&#9650;</span>}
      </span>
    </th>
  );
}

export function Tbody({ children }) {
  return <tbody className="divide-y divide-gray-100">{children}</tbody>;
}

export function Tr({ children, className = '', onClick }) {
  return (
    <tr
      className={`hover:bg-gray-50 transition ${onClick ? 'cursor-pointer' : ''} ${className}`}
      onClick={onClick}
    >
      {children}
    </tr>
  );
}

export function Td({ children, className = '' }) {
  return <td className={`px-4 py-3 text-gray-700 ${className}`}>{children}</td>;
}
