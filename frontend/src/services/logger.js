/**
 * PROMEOS — Structured Logger + Sentry Bridge
 * Usage: logger.error('Dashboard', 'Fetch failed', { status: 500 })
 * Sentry: optionnel — actif seulement si VITE_SENTRY_DSN est defini et @sentry/react installe.
 */

const LOG_LEVELS = { debug: 0, info: 1, warn: 2, error: 3 };

function log(level, tag, message, data) {
  const entry = { ts: new Date().toISOString(), level, tag, message, ...data };

  const fn = level === 'error' ? console.error : level === 'warn' ? console.warn : console.log;
  fn(`[${tag}] ${message}`, data || '');

  // Sentry bridge (error/warn only)
  if ((level === 'error' || level === 'warn') && typeof window !== 'undefined' && window.__SENTRY__) {
    try { window.Sentry?.captureMessage(`[${tag}] ${message}`, level); } catch { /* silent */ }
  }

  return entry;
}

export const logger = {
  debug: (tag, msg, data) => log('debug', tag, msg, data),
  info:  (tag, msg, data) => log('info', tag, msg, data),
  warn:  (tag, msg, data) => log('warn', tag, msg, data),
  error: (tag, msg, data) => log('error', tag, msg, data),
};

/**
 * initSentry — appeler une fois dans main.jsx.
 * Ne fait rien si VITE_SENTRY_DSN absent ou @sentry/react non installe.
 */
export function initSentry() {
  const dsn = import.meta.env.VITE_SENTRY_DSN;
  if (!dsn) return;
  // Dynamic import hidden from Rollup static analysis — @sentry/react is optional
  const pkg = '@sentry/' + 'react';
  import(/* @vite-ignore */ pkg).then(Sentry => {
    Sentry.init({ dsn, environment: import.meta.env.MODE });
    window.Sentry = Sentry;
    window.__SENTRY__ = true;
  }).catch(() => { /* @sentry/react not installed — silent */ });
}
