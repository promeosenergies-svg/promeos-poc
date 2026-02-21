/**
 * PROMEOS Design System — Toast System
 * ToastProvider renders a fixed container. useToast() hook provides toast(message, type).
 * Auto-dismiss after 4 seconds.
 */
import { createContext, useContext, useState, useCallback, useRef } from 'react';
import { CheckCircle, AlertTriangle, Info, XCircle, X } from 'lucide-react';

const ToastContext = createContext(null);

const TOAST_ICONS = {
  success: CheckCircle,
  error: XCircle,
  warning: AlertTriangle,
  info: Info,
};

const TOAST_STYLES = {
  success: 'bg-green-50 border-green-200 text-green-800',
  error: 'bg-red-50 border-red-200 text-red-800',
  warning: 'bg-amber-50 border-amber-200 text-amber-800',
  info: 'bg-blue-50 border-blue-200 text-blue-800',
};

let nextId = 0;

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const timers = useRef({});
  const recentMessages = useRef(new Map());

  const removeToast = useCallback((id) => {
    clearTimeout(timers.current[id]);
    delete timers.current[id];
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const toast = useCallback((message, type = 'info') => {
    // Dedup: skip if same message was shown in last 2 seconds
    const now = Date.now();
    const key = `${type}:${message}`;
    if (recentMessages.current.has(key) && now - recentMessages.current.get(key) < 2000) {
      return -1;
    }
    recentMessages.current.set(key, now);
    // Cleanup old entries to prevent memory leak
    if (recentMessages.current.size > 50) {
      for (const [k, ts] of recentMessages.current) {
        if (now - ts > 5000) recentMessages.current.delete(k);
      }
    }

    const id = ++nextId;
    setToasts((prev) => [...prev, { id, message, type }]);
    timers.current[id] = setTimeout(() => removeToast(id), 4000);
    return id;
  }, [removeToast]);

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      {/* Toast container */}
      <div className="fixed top-4 right-4 z-[60] flex flex-col gap-2 pointer-events-none" aria-live="polite">
        {toasts.map((t) => {
          const Icon = TOAST_ICONS[t.type] || TOAST_ICONS.info;
          const style = TOAST_STYLES[t.type] || TOAST_STYLES.info;
          return (
            <div
              key={t.id}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg border shadow-lg pointer-events-auto
                animate-[slideInRight_0.3s_ease-out] ${style}`}
            >
              <Icon size={18} className="shrink-0" />
              <span className="text-sm font-medium flex-1">{t.message}</span>
              <button
                onClick={() => removeToast(t.id)}
                className="p-0.5 rounded hover:bg-black/5 transition"
                aria-label="Fermer"
              >
                <X size={14} />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}
