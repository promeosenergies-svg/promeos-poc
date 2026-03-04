const variants = {
  primary:   'bg-blue-600 text-white hover:bg-blue-700 focus-visible:ring-blue-500',
  secondary: 'bg-gray-100 text-gray-700 hover:bg-gray-200 focus-visible:ring-gray-400',
  ghost:     'bg-transparent text-gray-600 hover:bg-gray-100 focus-visible:ring-gray-400',
  danger:    'bg-red-600 text-white hover:bg-red-700 focus-visible:ring-red-500',
};

const sizes = {
  sm: 'px-3 py-1.5 text-xs',
  md: 'px-4 py-2 text-sm',
  lg: 'px-5 py-2.5 text-base',
};

export default function Button({
  variant = 'primary', size = 'md', className = '', children, ...props
}) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 font-medium rounded-lg transition
        focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2
        disabled:opacity-50 disabled:cursor-not-allowed
        ${variants[variant]} ${sizes[size]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
