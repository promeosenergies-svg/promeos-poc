export default function Card({ className = '', children, ...props }) {
  return (
    <div className={`bg-white rounded-lg shadow-sm border border-gray-200 ${className}`} {...props}>
      {children}
    </div>
  );
}

export function CardHeader({ className = '', children }) {
  return <div className={`px-5 py-4 border-b border-gray-100 ${className}`}>{children}</div>;
}

export function CardBody({ className = '', children }) {
  return <div className={`px-5 py-4 ${className}`}>{children}</div>;
}
