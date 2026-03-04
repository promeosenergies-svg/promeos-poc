import { createContext, useContext } from 'react';

const TableCtx = createContext({ compact: false, pinFirst: false });

export function Table({ children, className = '', compact = false, pinFirst = false }) {
  return (
    <TableCtx.Provider value={{ compact, pinFirst }}>
      <div className={`overflow-x-auto ${className}`}>
        <table className="w-full text-sm">{children}</table>
      </div>
    </TableCtx.Provider>
  );
}

export function Thead({ children, sticky = false }) {
  return (
    <thead className={`bg-gray-50 border-b border-gray-200 ${sticky ? 'sticky top-0 z-[2]' : ''}`}>
      {children}
    </thead>
  );
}

export function Th({ children, className = '', sortable, sorted, onSort, pin }) {
  const { pinFirst } = useContext(TableCtx);
  const base = 'px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider';
  const pinCls = pin || (pinFirst && pin !== false) ? 'sticky left-0 z-[1] bg-gray-50' : '';

  if (!sortable) return <th className={`${base} ${pinCls} ${className}`}>{children}</th>;
  return (
    <th
      className={`${base} cursor-pointer select-none hover:text-gray-700 ${pinCls} ${className}`}
      onClick={onSort}
    >
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

export function Tr({ children, className = '', onClick, selected }) {
  return (
    <tr
      className={`hover:bg-gray-50 transition ${onClick ? 'cursor-pointer' : ''} ${selected ? 'bg-blue-50/60' : ''} ${className}`}
      onClick={onClick}
    >
      {children}
    </tr>
  );
}

export function Td({ children, className = '', pin }) {
  const { compact, pinFirst } = useContext(TableCtx);
  const py = compact ? 'py-2' : 'py-3';
  const pinCls =
    pin || (pinFirst && pin !== false) ? 'sticky left-0 z-[1] bg-white group-hover:bg-gray-50' : '';
  return (
    <td className={`px-4 ${py} text-gray-700 max-w-[240px] truncate ${pinCls} ${className}`}>
      {children}
    </td>
  );
}

export function ThCheckbox({ checked, onChange }) {
  return (
    <th className="px-4 py-3 w-10">
      <input
        type="checkbox"
        checked={checked}
        onChange={onChange}
        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
      />
    </th>
  );
}

export function TdCheckbox({ checked, onChange }) {
  const { compact } = useContext(TableCtx);
  const py = compact ? 'py-2' : 'py-3';
  return (
    <td className={`px-4 ${py}`} onClick={(e) => e.stopPropagation()}>
      <input
        type="checkbox"
        checked={checked}
        onChange={onChange}
        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
      />
    </td>
  );
}
