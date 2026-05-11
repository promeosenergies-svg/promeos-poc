/**
 * grammar/hub/states/HubError — Error block générique L11 (error state).
 *
 * Sprint Grammaire v1.2 / Phase 3.4 / Phase F.3 — extraction de ErrorBlock
 * inline depuis pages/CockpitJour.jsx vers le namespace canonique states/.
 *
 * Pattern alert in-place (pas une page d'erreur globale) : conserve le
 * shell de navigation et permet retry sans rechargement.
 *
 * Icone : `lucide-react.AlertTriangle` (le projet utilise lucide-react,
 * pas Tabler — cf grep package.json). Déviation documentée vs prompt
 * F.3 qui mentionnait `@tabler/icons-react`.
 *
 * correlationId copyable : un clic sur le badge mono copie la valeur
 * dans le clipboard (navigator.clipboard) puis affiche brièvement
 * "Copié ✓". Utile pour le support utilisateur (debug rapide).
 *
 * Source-guards : `data-component="HubError"` + `data-correlation-id`.
 * Display-only — zero calcul metier.
 *
 * @typedef {Object} HubErrorProps
 * @property {string} title              - Titre court (display Fraunces 17px)
 * @property {string} [description]      - Sous-titre body Inter 14px
 * @property {string} [correlationId]    - ID corrélation backend (badge mono copyable)
 * @property {() => void} [onRetry]      - Callback bouton Réessayer
 * @property {string} [className='']
 *
 * @param {HubErrorProps} props
 */
import { useState } from 'react';
import { AlertTriangle } from 'lucide-react';

async function copyToClipboard(text) {
  if (!text) return false;
  try {
    if (navigator?.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    /* clipboard API blocked (insecure context, perms) — fallback no-op */
  }
  return false;
}

export default function HubError({ title, description, correlationId, onRetry, className = '' }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    const ok = await copyToClipboard(correlationId);
    if (ok) {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    }
  };

  return (
    <div
      data-component="HubError"
      data-correlation-id={correlationId}
      role="alert"
      aria-live="polite"
      className={`rounded-xl border p-6 ${className}`}
      style={{
        background: 'var(--sol-refuse-bg)',
        borderColor: 'var(--sol-refuse-line)',
        color: 'var(--sol-refuse-fg)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '14px' }}>
        <AlertTriangle
          size={24}
          aria-hidden="true"
          style={{ color: 'var(--sol-attention-fg)', flexShrink: 0, marginTop: '2px' }}
        />
        <div style={{ flex: 1, minWidth: 0 }}>
          {title && (
            <h2
              style={{
                fontFamily: 'var(--sol-font-display)',
                fontSize: '17px',
                fontWeight: 500,
                lineHeight: 1.3,
                margin: '0 0 6px 0',
                color: 'var(--sol-refuse-fg)',
              }}
            >
              {title}
            </h2>
          )}
          {description && (
            <p
              style={{
                fontSize: '14px',
                lineHeight: 1.5,
                margin: '0 0 12px 0',
                color: 'var(--sol-refuse-fg)',
              }}
            >
              {description}
            </p>
          )}
          {correlationId && (
            <button
              type="button"
              onClick={handleCopy}
              aria-label={
                copied
                  ? 'Identifiant copie dans le presse-papier'
                  : `Copier l'identifiant ${correlationId}`
              }
              className="font-mono"
              style={{
                fontSize: '11px',
                padding: '3px 8px',
                borderRadius: '5px',
                background: 'var(--sol-bg-paper)',
                color: 'var(--sol-ink-700)',
                border: '1px solid var(--sol-rule)',
                cursor: 'pointer',
                marginRight: '8px',
              }}
            >
              {copied ? 'Copié ✓' : `ID ${correlationId}`}
            </button>
          )}
          {onRetry && (
            <button
              type="button"
              onClick={onRetry}
              className="font-mono"
              style={{
                fontSize: '12px',
                padding: '6px 12px',
                borderRadius: '7px',
                background: 'var(--sol-bg-paper)',
                color: 'var(--sol-refuse-fg)',
                border: '1px solid var(--sol-refuse-line)',
                cursor: 'pointer',
              }}
            >
              Réessayer
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
