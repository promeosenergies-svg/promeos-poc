/**
 * PROMEOS Design Tokens
 * Shared spacing, typography, color constants.
 */

export const colors = {
  primary: {
    50: '#eff6ff', 100: '#dbeafe', 200: '#bfdbfe',
    500: '#3b82f6', 600: '#2563eb', 700: '#1d4ed8',
  },
  success: { 50: '#f0fdf4', 500: '#22c55e', 700: '#15803d' },
  warning: { 50: '#fffbeb', 500: '#f59e0b', 700: '#b45309' },
  danger:  { 50: '#fef2f2', 500: '#ef4444', 700: '#b91c1c' },
  neutral: {
    50: '#f9fafb', 100: '#f3f4f6', 200: '#e5e7eb',
    300: '#d1d5db', 400: '#9ca3af', 500: '#6b7280',
    600: '#4b5563', 700: '#374151', 800: '#1f2937', 900: '#111827',
  },
};

export const spacing = {
  page: 'px-6 py-6',
  section: 'mb-6',
  card: 'p-5',
  gap: 'gap-4',
};

export const radius = {
  sm: 'rounded',
  md: 'rounded-lg',
  full: 'rounded-full',
};
